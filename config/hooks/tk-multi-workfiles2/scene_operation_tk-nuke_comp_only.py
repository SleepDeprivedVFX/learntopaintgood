# Copyright (c) 2026 SleepDeprivedVFX
#
# Custom scene operation hook for tk-nuke - comp-only Nuke Indie override.
#
# Nuke Indie always launches with Foundry's "Studio" application shell
# active (nuke.env['studio'] == True) - there's no separate "plain Nuke"
# mode for this license tier, even for pure NukeX compositing work. The
# stock tk-multi-workfiles2 hook for tk-nuke (scene_operation_tk-nuke.py,
# see its execute() method) treats studio_enabled as "the user is editing
# a Hiero/Nuke Studio Project" and routes File Save/Open through
# hiero.core project save/open logic, which requires exactly one Project
# Bin selected in the Timeline UI to disambiguate (_get_current_hiero_
# project -> "Please select a single Project!" if that selection isn't
# exactly one item).
#
# For comp-only work there is no meaningfully "selected" project - only
# Nuke Indie's always-present default blank Studio project - so that check
# fails on every save, even though the file actually being worked on is a
# plain .nkind comp script, not a Hiero project. Found 2026-09-06 - see
# DEVELOPMENT_NOTES.md.
#
# This hook is wired in for the comp Nuke contexts only (asset_step,
# shot_step - see tk-multi-workfiles2.yml) and simply ignores
# studio_enabled: File Save/Open/Save As always operate on the current
# Nuke script via nuke.scriptSave()/scriptOpen()/scriptSaveAs(), exactly
# like a classic non-Indie Nuke session - this is just the stock hook's
# classic-Nuke branch with the studio/hiero routing removed. It
# deliberately does NOT handle the Hiero/Nuke Studio Project case at all -
# if real Nuke-Studio-driven editorial is wired up later (see the
# deferred "project" block in tk-nuke.yml), that should go through the
# stock hiero-aware hook instead, not this one.

import os

import nuke

import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtGui

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Scene operation hook for comp-only Nuke Indie contexts. Always treats
    the current file as a plain Nuke script, regardless of Nuke Studio/
    Indie's "studio" application mode.
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
        """
        Main hook entry point - see scene_operation_tk-nuke.py for the
        full parameter/return contract this mirrors.
        """
        if file_path:
            file_path = file_path.replace(os.path.sep, "/")

        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace(os.path.sep, "/")

        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)

        elif operation == "save":
            # save the current script
            nuke.scriptSave()

        elif operation == "save_as":
            old_path = nuke.root()["name"].value()
            try:
                # rename script
                nuke.root()["name"].setValue(file_path)
                # save script
                nuke.scriptSaveAs(file_path, -1)
            except Exception as e:
                # something went wrong so reset to old path
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s" % e)

        elif operation == "reset":
            # Reset the scene to an empty state
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(
                    None,
                    "Save your script?",
                    "Your script has unsaved changes. Save before proceeding?",
                    QtGui.QMessageBox.Yes
                    | QtGui.QMessageBox.No
                    | QtGui.QMessageBox.Cancel,
                )

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()

            # now clear the script
            nuke.scriptClear()

            return True
