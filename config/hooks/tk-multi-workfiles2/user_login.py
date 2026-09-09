# Copyright (c) 2023 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Config-local override of tk-multi-workfiles2's default {self}/user_login.py.
See DEVELOPMENT_NOTES.md (2026-09-08) for the full writeup, including a
real-file test that found the deeper problem below.

THE ACTUAL PROBLEM (revised understanding, 2026-09-08):
The stock hook resolves the OS/filesystem owner of a work file (Windows:
NTFS owner via a Win32 API call; Mac/Linux: the file's Unix uid via pwd)
and returns that name directly as the "login" to match against ShotGrid's
HumanUser.login field. The first-pass fix here (see git history) assumed
the only problem was that name not matching a ShotGrid login, and added a
translation step driven by HumanUser.sg_sg_os_logins.

Testing against a real work file (the exact one from Adam's original
screenshot) found a second, more fundamental problem: the OS-owner lookup
itself often returns nothing at all, before any name-translation step
gets a chance to run. Root cause, confirmed against this file with both
this hook's own code and Windows' own `icacls`: this project has no
Active Directory, so every machine keeps its own private local Windows
account database. A file's NTFS owner isn't stored as a name - it's a
long machine-specific security ID (SID) - and a SID is only resolvable
back to a name on the exact machine that issued it. A file saved on one
machine and later browsed from File Open on a different machine will
fail to resolve *even if both machines happen to have a same-named local
account* - "sleep" on one machine and "sleep" on another are different
accounts with different SIDs. Windows surfaces this as error 1332,
ERROR_NONE_MAPPED. Given this pipeline is routinely used from more than
one physical machine (see the migration effort earlier in
DEVELOPMENT_NOTES.md), this is likely the dominant cause of "Unknown",
not just a name mismatch - and no mapping table can fix it, because the
lookup fails before there's anything to map.

THE FIX: stop relying on asking Windows/the filesystem who owns a file
after the fact, and instead have Toolkit stamp the correct ShotGrid login
itself at the moment of saving - using sgtk.util.get_current_user(),
exactly the API Adam originally proposed. At save time "the current
ShotGrid user" and "the author of this file" are provably the same thing
(unlike at file-listing time, where they can differ for every other
artist's file) - and it comes from the ShotGrid authentication session,
not any OS/Windows identity, so it's correct regardless of which machine
or OS account did the saving.

save_user() (called by tk-multi-workfiles2 right after a save) writes
that login into a small sidecar file next to the saved work file.
get_login() (called when listing files) reads the sidecar back directly
if present. This only covers files saved *after* this hook went live, so
the legacy OS-owner-lookup + sg_sg_os_logins-map path (see previous
docstring revision in git history for why that translation exists) is
kept as a fallback for older files - no worse than before for those, and
correct going forward for everything new, across every DCC via the
shared config/env/includes/settings/tk-multi-workfiles2.yml.

Onboarding a new artist / a new machine: nothing to configure for this
part at all - the very first file they save through workfiles2 stamps
their real ShotGrid login automatically. (The legacy sg_sg_os_logins
fallback below still requires registering + selecting their OS account
name in ShotGrid if you want *old, pre-existing* files attributed too;
see the previous docstring revision in git history for that flow.)
"""

import os
import threading

import sgtk


# Sidecar file suffix used to stamp the ShotGrid login of whoever saved a
# work file - see save_user()/get_login() and the module docstring above.
_STAMP_SUFFIX = ".sg_saved_by"

# Windows FILE_ATTRIBUTE_HIDDEN - see _hide_windows_file() below.
_FILE_ATTRIBUTE_HIDDEN = 0x02


def _stamp_path(work_path):
    """
    Path of the sidecar file save_user()/get_login() stamp/read the
    ShotGrid login from for work_path. Named with a leading dot so it's
    hidden by convention on Mac/Linux; _hide_windows_file() below covers
    the Windows half (a leading dot alone doesn't hide anything in
    Explorer).
    """
    dirname, basename = os.path.split(work_path)
    return os.path.join(dirname, "." + basename + _STAMP_SUFFIX)


def _hide_windows_file(path):
    """
    Set the Windows hidden attribute on path. No-op (silently) on
    Mac/Linux, or if the attribute call fails for any reason - the stamp
    file being visible is a cosmetic issue, never worth failing a save
    over.
    """
    if not sgtk.util.is_windows():
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetFileAttributesW(str(path), _FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass


HookClass = sgtk.get_hook_baseclass()

# Process-lifetime cache of the os-login -> shotgrid-login map built from
# HumanUser.sg_os_logins. Rebuilding on every file in a File Open listing
# would mean one ShotGrid query per file; this fetches the whole roster
# once per session instead. Lock guards against two file-listing threads
# (tk-multi-workfiles2 populates its file list on background threads)
# racing to build it at the same time - harmless either way, just avoids
# a duplicate query.
_os_login_map_cache = None
_os_login_map_lock = threading.Lock()


def _get_os_login_map(sg):
    """
    Fetch (and cache) the os-login -> shotgrid-login map from every
    HumanUser's sg_sg_os_logins field.

    :param sg: An authenticated Shotgun connection.
    :returns:  Dict of lowercased OS account name -> ShotGrid login.
    """
    global _os_login_map_cache

    with _os_login_map_lock:
        if _os_login_map_cache is not None:
            return _os_login_map_cache

        mapping = {}
        try:
            human_users = sg.find("HumanUser", [], ["login", "sg_sg_os_logins"])
        except Exception:
            # Field doesn't exist (yet), or the query failed for some
            # other reason - fall back to an empty map so get_login() just
            # returns the raw OS account name, same as stock behavior.
            human_users = []

        for human_user in human_users:
            sg_login = human_user.get("login")
            raw_os_logins = human_user.get("sg_sg_os_logins")
            if not sg_login or not raw_os_logins:
                continue
            # A ShotGrid `list` field comes back as a plain string if it's
            # single-select, or a list of strings if multi-select is
            # enabled - handle both without needing to know which.
            os_logins = (
                raw_os_logins if isinstance(raw_os_logins, list) else [raw_os_logins]
            )
            for os_login in os_logins:
                os_login = (os_login or "").strip().lower()
                if os_login:
                    mapping[os_login] = sg_login

        _os_login_map_cache = mapping
        return _os_login_map_cache


class UserLogin(HookClass):
    """
    Hook that can be used to push and retrieve user login data for work files.
    """

    def get_login(self, path, **kwargs):
        """
        This method is called when listing all the work files. Prefers the
        ShotGrid login stamped by save_user() at save time (reliable
        regardless of machine/OS account - see module docstring); falls
        back to the legacy OS-owner lookup + sg_sg_os_logins map for files
        saved before this hook existed.

        :param path:            Path where the work file is located.
        :type path:             str

        :returns:               The login name printed on the file metadata, otherwise None.
        :rtype:                 Optional[str]
        """
        stamped_login = self._read_stamped_login(path)
        if stamped_login:
            return stamped_login

        os_login = self._get_os_login(path)
        if not os_login:
            return None

        try:
            mapping = _get_os_login_map(self.parent.shotgun)
        except Exception:
            mapping = {}

        return mapping.get(os_login.lower(), os_login)

    def _read_stamped_login(self, path):
        """
        Read back the ShotGrid login save_user() stamped for this file, if
        any.
        """
        try:
            with open(_stamp_path(path), "r") as stamp_file:
                return stamp_file.read().strip() or None
        except Exception:
            return None

    def _get_os_login(self, path):
        """
        OS-level file owner lookup - identical to the stock hook's logic,
        just factored out so USER_LOGIN_MAP can be applied to its result.
        """
        if sgtk.util.is_windows():
            # Get this information for Windows platforms
            try:
                return Win32Api().get_file_owner(path)
            except Exception:
                return None
        else:
            # Get this information for Linux and Darwin platforms
            try:
                from pwd import getpwuid

                return getpwuid(os.stat(path).st_uid).pw_name
            except Exception:
                return None

    def save_user(self, work_path, work_version, **kwargs):
        """
        Called by tk-multi-workfiles2 right after a work file is saved.
        Stamps the currently-authenticated ShotGrid user's login into a
        sidecar file next to work_path, so get_login() can read it back
        directly later - see module docstring for why this replaces
        relying on OS/filesystem file ownership.

        :param work_path:       Path where the work file was saved.
        :type work_path:        str

        :param work_version:    Version of the work file that was saved.
        :type work_version:     int

        :returns:               None
        """
        try:
            current_user = sgtk.util.get_current_user(self.parent.sgtk)
            login = current_user.get("login") if current_user else None
        except Exception:
            login = None

        if not login:
            # No authenticated ShotGrid user available (e.g. a script-based
            # session) - nothing reliable to stamp. get_login() will fall
            # back to the legacy OS-owner lookup for this file.
            return

        stamp_path = _stamp_path(work_path)
        try:
            with open(stamp_path, "w") as stamp_file:
                stamp_file.write(login)
            _hide_windows_file(stamp_path)
        except Exception:
            # Never let a metadata-stamping failure block the save itself.
            self.parent.logger.warning(
                "Couldn't stamp ShotGrid login for %s" % work_path, exc_info=True
            )


class Win32Api:
    """
    Helper class to access Windows APIs.

    Reference: https://github.com/shotgunsoftware/tk-multi-workfiles2/pull/4/files
    By @skral
    """

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self._PSECURITY_DESCRIPTOR = ctypes.POINTER(wintypes.BYTE)
        self._PSID = ctypes.POINTER(wintypes.BYTE)
        self._LPDWORD = ctypes.POINTER(wintypes.DWORD)
        self._LPBOOL = ctypes.POINTER(wintypes.BOOL)

        self._OWNER_SECURITY_INFORMATION = 0x00000001
        self._SID_TYPES = dict(
            enumerate(
                "User Group Domain Alias WellKnownGroup DeletedAccount "
                "Invalid Unknown Computer Label".split(),
                1,
            )
        )

        self._advapi32 = ctypes.windll.advapi32

        # MSDN windows/desktop/aa446639
        self._GetFileSecurity = self._advapi32.GetFileSecurityW
        self._GetFileSecurity.restype = wintypes.BOOL
        self._GetFileSecurity.argtypes = [
            wintypes.LPCWSTR,  # File Name (in)
            wintypes.DWORD,  # Requested Information (in)
            self._PSECURITY_DESCRIPTOR,  # Security Descriptor (out_opt)
            wintypes.DWORD,  # Length (in)
            self._LPDWORD,  # Length Needed (out)
        ]

        # MSDN windows/desktop/aa446651
        self._GetSecurityDescriptorOwner = self._advapi32.GetSecurityDescriptorOwner
        self._GetSecurityDescriptorOwner.restype = wintypes.BOOL
        self._GetSecurityDescriptorOwner.argtypes = [
            self._PSECURITY_DESCRIPTOR,  # Security Descriptor (in)
            ctypes.POINTER(self._PSID),  # Owner (out)
            self._LPBOOL,  # Owner Exists (out)
        ]

        # MSDN windows/desktop/aa379166
        self._LookupAccountSid = self._advapi32.LookupAccountSidW
        self._LookupAccountSid.restype = wintypes.BOOL
        self._LookupAccountSid.argtypes = [
            wintypes.LPCWSTR,  # System Name (in)
            self._PSID,  # SID (in)
            wintypes.LPCWSTR,  # Name (out)
            self._LPDWORD,  # Name Size (inout)
            wintypes.LPCWSTR,  # Domain(out_opt)
            self._LPDWORD,  # Domain Size (inout)
            self._LPDWORD,  # SID Type (out)
        ]

        # Make available these modules for the object
        self.ctypes = ctypes
        self.wintypes = wintypes

    def get_file_security(self, filename, request):
        length = self.wintypes.DWORD()
        self._GetFileSecurity(filename, request, None, 0, self.ctypes.byref(length))

        if length.value:
            sd = (self.wintypes.BYTE * length.value)()
            if self._GetFileSecurity(
                filename, request, sd, length, self.ctypes.byref(length)
            ):
                return sd

    def get_security_descriptor_owner(self, sd):
        if sd is not None:
            sid = self._PSID()
            sid_defaulted = self.wintypes.BOOL()

            if self._GetSecurityDescriptorOwner(
                sd, self.ctypes.byref(sid), self.ctypes.byref(sid_defaulted)
            ):
                return sid

    def look_up_account_sid(self, sid):
        if sid is not None:
            SIZE = 256
            name = self.ctypes.create_unicode_buffer(SIZE)
            domain = self.ctypes.create_unicode_buffer(SIZE)
            cch_name = self.wintypes.DWORD(SIZE)
            cch_domain = self.wintypes.DWORD(SIZE)
            sid_type = self.wintypes.DWORD()

            if self._LookupAccountSid(
                None,
                sid,
                name,
                self.ctypes.byref(cch_name),
                domain,
                self.ctypes.byref(cch_domain),
                self.ctypes.byref(sid_type),
            ):
                return name.value, domain.value, sid_type.value

        return None, None, None

    def get_file_owner(self, path):
        request = self._OWNER_SECURITY_INFORMATION

        sd = self.get_file_security(path, request)
        sid = self.get_security_descriptor_owner(sd)
        name, domain, sid_type = self.look_up_account_sid(sid)
        return name
