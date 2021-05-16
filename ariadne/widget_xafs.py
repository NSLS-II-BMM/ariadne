import copy
import xraylib
import re

from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QComboBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QPushButton,
    QTableWidget,
    QAbstractItemView,
    QTableView,
    QButtonGroup,
    QTableWidgetItem,
)
from qtpy.QtGui import QPalette, QBrush, QColor
from qtpy.QtCore import Qt, Signal, Slot


# The following LineEdit widgets are copied from PyXRF code


class LineEditExtended(QLineEdit):
    """
    LineEditExtended allows to mark the displayed value as invalid by setting
    its `valid` property to False. By default, the text color is changed to Light Red.
    It also emits `focusOut` signal at `self.focusOutEvent`.
    """

    # Emitted at focusOutEvent
    focusOut = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid = True
        self._style_sheet_valid = ""  # By default, clear the style sheet
        self._style_sheet_invalid = "color: rgb(255, 0, 0);"
        self._update_valid_status()

    def _update_valid_status(self):
        if self._valid:
            super().setStyleSheet(self._style_sheet_valid)
        else:
            super().setStyleSheet(self._style_sheet_invalid)

    def setStyleSheet(self, style_sheet, *, valid=True):
        """
        Set style sheet for valid/invalid states. If call with one parameter, the function
        works the same as `setStyleSheet` of QWidget. If `valid` is set to `False`, the
        supplied style sheet will be applied only if 'invalid' state is activated. The
        style sheets for the valid and invalid states are independent and can be set
        separately.

        The default behavior: 'valid' state - clear style sheet, 'invalid' state -
        use the style sheet `"color: rgb(255, 0, 0);"`

        Parameters
        ----------
        style_sheet: str
            style sheet
        valid: bool
            True - activate 'valid' state, False - activate 'invalid' state
        """
        if valid:
            self._style_sheet_valid = style_sheet
        else:
            self._style_sheet_invalid = style_sheet
        self._update_valid_status()

    def getStyleSheet(self, *, valid):
        """
        Return the style sheet used 'valid' or 'invalid' state.

        Parameters
        ----------
        valid: bool
            True/False - return the style sheet that was set for 'valid'/'invalid' state.
        """
        if valid:
            return self._style_sheet_valid
        else:
            return self._style_sheet_invalid

    def setValid(self, state):
        """Set the state of the line edit box.: True - 'valid', False - 'invalid'"""
        self._valid = bool(state)
        self._update_valid_status()

    def isValid(self):
        """
        Returns 'valid' status of the line edit box (bool).
        """
        return self._valid

    def focusOutEvent(self, event):
        """
        Overriddent QWidget method. Sends custom 'focusOut()' signal
        """
        super().focusOutEvent(event)
        self.focusOut.emit()


class LineEditReadOnly(LineEditExtended):
    """
    Read-only version of QLineEdit with background set to the same color
    as the background of the disabled QLineEdit, but font color the same
    as active QLineEdit.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        p = self.palette()
        self._color_bckg = p.color(QPalette.Active, QPalette.Base)
        self._color_disabled = p.color(QPalette.Disabled, QPalette.Base)
        self.setReadOnly(True)

    def setReadOnly(self, read_only):
        super().setReadOnly(read_only)
        color = self._color_disabled if read_only else self._color_bckg
        p = self.palette()
        p.setColor(QPalette.Base, color)
        self.setPalette(p)


class PlanEditorXafs(QWidget):

    signal_update_widgets = Signal()
    signal_update_selection = Signal(object)

    def __init__(self, model, parent=None, *, editable=False, detailed=True):
        super().__init__(parent)
        self.model = model

        self._edit_mode = False
        self._parameters = {}
        self._parameters_backup = self._get_default_parameters()
        self._parameters_last_submitted = self._get_default_parameters()
        self._item_currently_loaded = {}

        self._n_selected_region = -1

        self._plan_empty = True  # Start with empty plan/form
        self._plan_valid = False  # Set True if widget state represent a valid plan
        self._edit_mode = False  # False - view mode, True - edit mode
        self._plan_new = False  # Editing new plan

        self._ignore_table_events = False

        self._text_color_valid = QTableWidgetItem().foreground()
        self._text_color_invalid = QBrush(QColor(255, 0, 0))

        self._lb_mode = QLabel("")
        self._pb_edit = QPushButton("Edit")
        self._pb_edit.clicked.connect(self._pb_edit_clicked)
        self._pb_new = QPushButton("New")
        self._pb_new.clicked.connect(self._pb_new_clicked)

        self._combo_element = QComboBox()
        self._combo_element_list = self._get_full_element_list()
        self._combo_element.addItems(self._combo_element_list)
        self._combo_element.setEditable(False)
        self._combo_element.currentIndexChanged.connect(self._combo_element_current_index_changed)

        self._combo_edge = QComboBox()
        self._combo_edge_list = ("K", "L1", "L2", "L3")
        self._combo_edge.addItems(self._combo_edge_list)
        self._combo_edge.setEditable(False)
        self._combo_edge.currentIndexChanged.connect(self._combo_edge_current_index_changed)

        self._combo_mode = QComboBox()
        self._combo_mode_list = ("transmission", "fluorescence", "both")
        self._combo_mode.addItems(self._combo_mode_list)
        self._combo_mode.setEditable(False)
        self._combo_mode.currentIndexChanged.connect(self._combo_mode_current_index_changed)

        self._le_sample = LineEditReadOnly()
        self._le_preparation = LineEditReadOnly()
        self._le_comment = LineEditReadOnly()
        self._le_sample.editingFinished.connect(self._le_sample_editing_finished)
        self._le_preparation.editingFinished.connect(self._le_preparation_editing_finished)
        self._le_comment.editingFinished.connect(self._le_comment_editing_finished)

        self._le_number_of_scans = LineEditReadOnly()
        self._le_number_of_scans.textChanged.connect(self._le_number_of_scans_text_changed)
        self._le_number_of_scans.editingFinished.connect(self._le_number_of_scans_editing_finished)

        self._le_filename = LineEditReadOnly()
        self._le_filename.textChanged.connect(self._le_filename_text_changed)
        self._le_filename.editingFinished.connect(self._le_filename_editing_finished)

        self._le_start = LineEditReadOnly()
        self._le_start.textChanged.connect(self._le_start_text_changed)
        self._le_start.editingFinished.connect(self._le_start_editing_finished)

        self._rb_start_next = QRadioButton("'next'")
        self._rb_start_next.clicked.connect(self._rb_start_next_clicked)
        self._rb_start_number = QRadioButton()
        self._rb_start_number.clicked.connect(self._rb_start_number_clicked)
        self._bgroup_start = QButtonGroup()
        self._bgroup_start.addButton(self._rb_start_next)
        self._bgroup_start.addButton(self._rb_start_number)

        self._pb_split = QPushButton("Split Region")
        self._pb_split.clicked.connect(self._pb_split_clicked)
        self._pb_delete = QPushButton("Delete Region")
        self._pb_delete.clicked.connect(self._pb_delete_clicked)

        self._pb_add_to_queue = QPushButton("Add to Queue")
        self._pb_add_to_queue.clicked.connect(self._pb_add_to_queue_clicked)
        self._pb_save = QPushButton("Save")
        self._pb_save.clicked.connect(self._pb_save_clicked)
        self._pb_reset = QPushButton("Reset")
        self._pb_reset.clicked.connect(self._pb_reset_clicked)
        self._pb_cancel = QPushButton("Cancel")
        self._pb_cancel.clicked.connect(self._pb_cancel_clicked)

        # Set up table
        self._table = QTableWidget()
        self._table_column_labels = ("Low", "High", "Step", "Time")
        self._table.setColumnCount(len(self._table_column_labels))
        self._table.verticalHeader().hide()

        self._table.setHorizontalHeaderLabels(self._table_column_labels)

        self._table.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)

        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setShowGrid(True)

        self._table.setAlternatingRowColors(True)

        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setMinimumSectionSize(5)

        self._table.itemSelectionChanged.connect(self._table_item_selection_changed)
        self._table.cellChanged.connect(self._table_cell_changed)

        vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(QLabel("XAFS PLAN"))
        hbox.addStretch(1)
        hbox.addWidget(self._lb_mode)
        hbox.addWidget(self._pb_edit)
        hbox.addWidget(self._pb_new)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Element:"))
        hbox.addWidget(self._combo_element, stretch=2)
        hbox.addStretch(1)
        hbox.addWidget(QLabel("Edge:"))
        hbox.addWidget(self._combo_edge, stretch=2)
        hbox.addStretch(1)
        hbox.addWidget(QLabel("Mode:"))
        hbox.addWidget(self._combo_mode, stretch=2)
        vbox.addLayout(hbox)

        grid = QGridLayout()
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        grid.addWidget(QLabel("Sample:"), 1, 0, alignment=Qt.AlignLeft)
        grid.addWidget(self._le_sample, 1, 1)
        grid.addWidget(QLabel("Preparation:"), 1, 2, alignment=Qt.AlignLeft)
        grid.addWidget(self._le_preparation, 1, 3)

        grid.addWidget(QLabel("Comment:"), 2, 0, alignment=Qt.AlignRight)
        grid.addWidget(self._le_comment, 2, 1, 1, 3)

        vbox.addLayout(grid)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Number of scans:"))
        hbox.addWidget(self._le_number_of_scans, stretch=1)
        hbox.addStretch(1)
        hbox.addWidget(QLabel("Start:"))
        hbox.addWidget(self._rb_start_next)
        hbox.addWidget(self._rb_start_number)
        hbox.addWidget(self._le_start, stretch=1)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("File name:"))
        hbox.addWidget(self._le_filename)
        hbox.addStretch(1)
        hbox.addWidget(self._pb_split)
        hbox.addWidget(self._pb_delete)
        vbox.addLayout(hbox)

        vbox.addWidget(self._table)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._pb_add_to_queue)
        hbox.addWidget(self._pb_save)
        hbox.addWidget(self._pb_reset)
        hbox.addWidget(self._pb_cancel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self._update_widgets()

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

        self.model.events.queue_item_selection_changed.connect(self.on_queue_item_selection_changed)
        self.signal_update_selection.connect(self.slot_view_item)

    def _get_full_element_list(self):
        """
        Returns the list of all elements in the order of atomic numbers (1..107)
        """
        return [xraylib.AtomicNumberToSymbol(_) for _ in range(1, 108)]

    def _get_default_parameters(self):
        """
        Return the default set of parameters. The parameters are not equivalent to
        the plan parameters, but instead define the state of GUI elements.
        The set of parameters is sufficient to generate a set of plan parameters
        using straightforward formatting algorithm
        """
        default_parameters = {
            "element": "Fe",
            "edge": "K",
            "sample": "--sample--",
            "preparation": "--preparation--",
            "comment": "--comment--",
            "nscans": "1",
            "start_next": True,
            "start_number": 1,
            "mode": "transmission",
            "bounds": ["-200", "-30", "-10", "30", "200"],
            "steps": ["10", "2", "0.2", "0.5"],
            "times": ["1", "1", "1", "1"],
            "filename": "",
        }
        return copy.deepcopy(default_parameters)

    def _clear_widgets(self):
        self._combo_element.setCurrentIndex(-1)
        self._combo_edge.setCurrentIndex(-1)
        self._combo_mode.setCurrentIndex(-1)

        self._le_sample.setText("")
        self._le_preparation.setText("")
        self._le_comment.setText("")

        self._le_number_of_scans.setText("")

        self._set_widgets_start_next(True)
        self._le_start.setText("")

        self._le_filename.setText("")

        self._clear_table()
        self._update_widget_state()

    def _fill_widgets(self):
        def find_index(lst, val):
            try:
                return lst.index(val)
            except ValueError:
                return -1

        ind_element = find_index(self._combo_element_list, self._parameters["element"])
        self._combo_element.setCurrentIndex(ind_element)

        ind_edge = find_index(self._combo_edge_list, self._parameters["edge"])
        self._combo_edge.setCurrentIndex(ind_edge)

        ind_mode = find_index(self._combo_mode_list, self._parameters["mode"])
        self._combo_mode.setCurrentIndex(ind_mode)

        # Setting cursor to position 0 after setting the text makes QLineEdit
        #   always show the beginning of the string if the string is too long to fit.
        self._le_sample.setText(f"{self._parameters['sample']}")
        self._le_sample.setCursorPosition(0)
        self._le_preparation.setText(f"{self._parameters['preparation']}")
        self._le_preparation.setCursorPosition(0)
        self._le_comment.setText(f"{self._parameters['comment']}")
        self._le_comment.setCursorPosition(0)

        self._le_number_of_scans.setText(f"{self._parameters['nscans']}")

        start_next = self._parameters["start_next"]
        start_number = self._parameters["start_number"]
        self._set_widgets_start_next(start_next)
        self._le_start.setText(f"{start_number}")

        self._le_filename.setText(f"{self._parameters['filename']}")

        self._fill_table()
        self._update_widget_state()
        self._validate_widgets()

    def _update_widgets(self):
        if self._plan_empty:
            self._clear_widgets()
        else:
            self._fill_widgets()

    def _clear_table(self):
        self._table.clearContents()
        self._table.setRowCount(0)

    def _fill_table(self):

        self._ignore_table_events = True

        n_selected_region = self._n_selected_region

        self._clear_table()

        bounds = self._parameters["bounds"]
        steps = self._parameters["steps"]
        times = self._parameters["times"]

        n_bounds = len(bounds) - 1 if bounds else 0
        n_steps = len(steps)
        n_times = len(times)

        if n_bounds and (n_bounds == n_steps) and (n_steps == n_times):

            self._table.setRowCount(n_bounds)

            for n in range(n_bounds):
                v_low = bounds[n]
                v_high = bounds[n + 1]
                v_steps = steps[n]
                v_time = times[n]

                item_low = QTableWidgetItem(f"{v_low}")
                self._table.setItem(n, 0, item_low)
                item_high = QTableWidgetItem(f"{v_high}")
                if n < n_bounds - 1:
                    item_high.setFlags(item_high.flags() & ~Qt.ItemIsEnabled)
                self._table.setItem(n, 1, item_high)
                item_steps = QTableWidgetItem(f"{v_steps}")
                self._table.setItem(n, 2, item_steps)
                item_time = QTableWidgetItem(f"{v_time}")
                self._table.setItem(n, 3, item_time)

            self.select_region(n_selected_region)

        elif n_bounds:
            print(
                f"The number of regions does not match the number of steps or times: "
                f"n_bounds={n_bounds} n_steps={n_steps} n_times={n_times}"
            )

        self._ignore_table_events = False

    def select_region(self, n_region):
        if 0 <= n_region < len(self._parameters["steps"]):
            self._table.selectRow(n_region)
        else:
            self._table.clearSelection()

    def _set_table_read_only(self, read_only):
        self._ignore_table_events = True

        for n_row in range(self._table.rowCount()):
            for n_col in range(self._table.columnCount()):
                item = self._table.item(n_row, n_col)
                if read_only:
                    flags = item.flags() & ~Qt.ItemIsEditable
                else:
                    flags = item.flags() | Qt.ItemIsEditable
                item.setFlags(flags)

        self._ignore_table_events = False

    def _update_widget_state(self):
        is_connected = bool(self.model.re_manager_connected)

        if self._plan_empty:
            self._lb_mode.setVisible(False)
            self._pb_edit.setVisible(False)
            self._pb_new.setVisible(True)
            self._pb_new.setEnabled(is_connected)

            self._combo_element.setEnabled(False)
            self._combo_edge.setEnabled(False)
            self._combo_mode.setEnabled(False)

            self._le_sample.setEnabled(False)
            self._le_preparation.setEnabled(False)
            self._le_comment.setEnabled(False)

            self._le_number_of_scans.setEnabled(False)
            self._rb_start_next.setEnabled(False)
            self._rb_start_number.setEnabled(False)
            self._le_start.setEnabled(False)

            self._le_filename.setEnabled(False)

            self._pb_split.setEnabled(False)
            self._pb_delete.setEnabled(False)

            self._table.setEnabled(False)

            self._pb_save.setEnabled(False)
            self._pb_add_to_queue.setEnabled(False)
            self._pb_cancel.setEnabled(False)
            self._pb_reset.setEnabled(False)

        else:
            region_selected = self._n_selected_region >= 0
            more_than_one_region = len(self._parameters["steps"]) > 1
            plan_valid = self._plan_valid
            plan_new = self._plan_new
            edit_mode = self._edit_mode

            if edit_mode:
                text = "NEW PLAN" if plan_new else "QUEUE PLAN"
                self._lb_mode.setText(text)
                self._lb_mode.setVisible(True)
                self._pb_edit.setVisible(False)
                self._pb_new.setVisible(False)
            else:
                self._lb_mode.setVisible(False)
                self._pb_edit.setVisible(True)
                self._pb_new.setVisible(True)

            self._pb_edit.setEnabled(is_connected)
            self._pb_new.setEnabled(is_connected)

            self._combo_element.setEnabled(edit_mode)
            self._combo_edge.setEnabled(edit_mode)
            self._combo_mode.setEnabled(edit_mode)

            self._le_sample.setEnabled(True)
            self._le_preparation.setEnabled(True)
            self._le_comment.setEnabled(True)
            self._le_sample.setReadOnly(not edit_mode)
            self._le_preparation.setReadOnly(not edit_mode)
            self._le_comment.setReadOnly(not edit_mode)

            self._le_number_of_scans.setEnabled(True)
            self._le_number_of_scans.setReadOnly(not edit_mode)
            self._rb_start_next.setEnabled(edit_mode)
            self._rb_start_number.setEnabled(edit_mode)
            self._le_start.setReadOnly(not edit_mode)

            self._le_filename.setEnabled(True)
            self._le_filename.setReadOnly(not edit_mode)

            self._pb_split.setEnabled(edit_mode and region_selected)
            self._pb_delete.setEnabled(edit_mode and region_selected and more_than_one_region)

            self._table.setEnabled(True)
            self._set_table_read_only(not edit_mode)

            self._pb_save.setEnabled(is_connected and edit_mode and plan_valid and not plan_new)
            self._pb_add_to_queue.setEnabled(is_connected and edit_mode and plan_valid)
            self._pb_cancel.setEnabled(edit_mode)
            self._pb_reset.setEnabled(edit_mode)

    def _combo_element_current_index_changed(self, index):
        if index >= 0:
            self._parameters["element"] = self._combo_element.currentText()

    def _combo_edge_current_index_changed(self, index):
        if index >= 0:
            self._parameters["edge"] = self._combo_edge.currentText()

    def _combo_mode_current_index_changed(self, index):
        if index >= 0:
            self._parameters["mode"] = self._combo_mode.currentText()

    def _le_sample_editing_finished(self):
        text = self._le_sample.text().strip()
        self._le_sample.setText(text)
        self._le_sample.setCursorPosition(0)
        self._parameters["sample"] = text

    def _le_preparation_editing_finished(self):
        text = self._le_preparation.text().strip()
        self._le_preparation.setText(text)
        self._le_preparation.setCursorPosition(0)
        self._parameters["preparation"] = text

    def _le_comment_editing_finished(self):
        text = self._le_comment.text().strip()
        self._le_comment.setText(text)
        self._le_comment.setCursorPosition(0)
        self._parameters["comment"] = text
        print(f"Changed comment: '{text}'")

    def _is_int(self, text, *, min=None, max=None):
        try:
            v = int(text)
            if (min is not None) and (v < min):
                return False
            if (max is not None) and (v > max):
                return False
        except ValueError:
            return False
        return True

    def _le_number_of_scans_text_changed(self, text):
        self._le_number_of_scans.setValid(self._is_int(text, min=1))

    def _le_number_of_scans_editing_finished(self):
        if self._le_number_of_scans.isValid():
            text = self._le_number_of_scans.text()
            try:
                self._parameters["nscans"] = int(text)
            except ValueError:
                pass
        self._le_number_of_scans.setText(f"{self._parameters['nscans']}")

    def _le_start_text_changed(self, text):
        self._le_start.setValid(self._is_int(text, min=1))

    def _le_start_editing_finished(self):
        if self._le_start.isValid():
            text = self._le_start.text()
            try:
                self._parameters["start_number"] = int(text)
            except ValueError:
                pass
        self._le_start.setText(f"{self._parameters['start_number']}")

    def _set_widgets_start_next(self, start_next_on):
        self._parameters["start_next"] = start_next_on
        self._rb_start_next.setChecked(start_next_on)
        self._rb_start_number.setChecked(not start_next_on)
        self._le_start.setEnabled(not start_next_on)

    def _rb_start_next_clicked(self, checked):
        if checked:
            self._set_widgets_start_next(True)

    def _rb_start_number_clicked(self, checked):
        if checked:
            self._set_widgets_start_next(False)

    def _validate_filename(self, filename):
        return bool(re.search(r"^[0-9A-Za-z\.\-+_]+$", filename))

    def _le_filename_text_changed(self, text):
        self._le_filename.setValid(self._validate_filename(text))

    def _le_filename_editing_finished(self):
        text = self._le_filename.text().strip()
        if self._validate_filename(text):
            self._parameters["filename"] = text
        self._le_filename.setText(self._parameters["filename"])
        self._le_filename.setCursorPosition(0)

    def _delete_region(self):
        sel_region = self._n_selected_region
        n_regions = len(self._parameters["steps"])
        is_last = sel_region == n_regions - 1

        # Do nothing if only 1 region is left
        if (n_regions > 1) and (0 <= sel_region < n_regions):
            if sel_region:
                self._parameters["bounds"].pop(sel_region)
            else:
                self._parameters["bounds"].pop(sel_region + 1)
            self._parameters["steps"].pop(sel_region)
            self._parameters["times"].pop(sel_region)
            if is_last:
                self._n_selected_region -= 1
            self._update_widgets()

    def _interpret_boundary_value(self, bound_val):
        bv = bound_val.strip().lower()
        is_wavenumber = bv.endswith("k")
        bv = bv[:-1] if is_wavenumber else bv
        try:
            bv = float(bv)
            bv_energy = 3.81 * bv ** 2 if is_wavenumber else bv
        except ValueError:
            raise ValueError(f"Boundary value '{bound_val}' is incorrectly formatted or out of range")
        return bv, bv_energy, is_wavenumber

    def _split_region(self):
        sel_region = self._n_selected_region
        n_regions = len(self._parameters["steps"])
        if 0 <= sel_region < n_regions:
            try:
                bounds = self._parameters["bounds"]
                bv1, bv_energy1, is_wavenumber1 = self._interpret_boundary_value(bounds[sel_region])
                bv2, bv_energy2, is_wavenumber2 = self._interpret_boundary_value(bounds[sel_region + 1])
                if (is_wavenumber1 and is_wavenumber2) or (not is_wavenumber1 and not is_wavenumber2):
                    bv_center = f"{(bv1 + bv2) / 2}"
                    if is_wavenumber1:
                        bv_center += "k"
                else:
                    bv_center = f"{(bv_energy1 + bv_energy2) / 2}"

                new_bound = bv_center
                bounds.insert(sel_region + 1, new_bound)
                self._parameters["steps"].insert(sel_region + 1, self._parameters["steps"][sel_region])
                self._parameters["times"].insert(sel_region + 1, self._parameters["times"][sel_region])
                self._update_widgets()
            except ValueError as ex:
                print(f"Failed to split the region: {ex}")

    def _pb_split_clicked(self):
        self._split_region()

    def _pb_delete_clicked(self):
        self._delete_region()

    def _table_item_selection_changed(self):
        sel_rows = self._table.selectionModel().selectedRows()
        # It is assumed that only one row may be selected at a time. If the table settings change
        #   so that more than one row could be selected at a time, the following code will not work.
        try:
            if len(sel_rows) >= 1:
                row = sel_rows[0].row()
                self._n_selected_region = row
            else:
                raise Exception()
        except Exception:
            self._n_selected_region = -1

        self._update_widget_state()

    def _table_cell_changed(self, row, column):
        if self._ignore_table_events:
            return

        table_item = self._table.item(row, column)
        text = table_item.text()
        text = text.strip().lower()

        if column in (0, 1):
            data = self._parameters["bounds"]
        elif column == 2:
            data = self._parameters["steps"]
        elif column == 3:
            data = self._parameters["times"]
        else:
            return

        try:
            _, v_energy, _ = self._interpret_boundary_value(text)
            if column == 0:
                data[row] = text
            elif column in (2, 3):
                if v_energy > 0:
                    data[row] = text
            elif column == 1:
                data[row + 1] = text
        except ValueError:
            pass

        self._update_widgets()

    def _validate_table(self):
        self._ignore_table_events = True

        table_valid = True
        n_rows = self._table.rowCount()

        for n_row in range(n_rows):
            for n_col in range(4):
                table_item = self._table.item(n_row, n_col)
                if table_item.flags() & Qt.ItemIsEnabled:
                    try:
                        self._interpret_boundary_value(table_item.text())
                        cell_valid = True
                    except Exception:
                        table_valid = False
                        cell_valid = False

                    table_item.setForeground(self._text_color_valid if cell_valid else self._text_color_invalid)

        # If the table is still valid, then check the order of the region bounds
        if table_valid:
            for n_row in range(n_rows):
                _, bv_energy1, _ = self._interpret_boundary_value(self._parameters["bounds"][n_row])
                _, bv_energy2, _ = self._interpret_boundary_value(self._parameters["bounds"][n_row + 1])
                if bv_energy1 >= bv_energy2:
                    table_item1 = self._table.item(n_row, 0)
                    n_row2 = n_row + 1 if (n_row < n_rows - 1) else n_row
                    n_col2 = 0 if (n_row < n_rows - 1) else 1
                    table_item2 = self._table.item(n_row2, n_col2)

                    table_item1.setForeground(self._text_color_invalid)
                    table_item2.setForeground(self._text_color_invalid)

                    table_valid = False

        self._ignore_table_events = False

        if not table_valid:
            self._table.clearSelection()

        return table_valid

    def _validate_widgets(self):
        is_valid = self._validate_table()

        if self._combo_element.currentIndex() < 0:
            is_valid = False
        if self._combo_edge.currentIndex() < 0:
            is_valid = False
        if self._combo_mode.currentIndex() < 0:
            is_valid = False

        try:
            int(self._le_number_of_scans.text())
            if self._rb_start_number.isChecked():
                int(self._le_start)
        except Exception:
            is_valid = False

        self._plan_valid = is_valid
        self._update_widget_state()

    def _pb_edit_clicked(self):
        # Start editing the plan that is currently open in 'View' mode
        self._parameters_backup = copy.deepcopy(self._parameters)
        self._plan_empty = False
        self._edit_mode = True
        self._plan_new = False
        self._update_widgets()

    def _pb_new_clicked(self):
        self._parameters = copy.deepcopy(self._parameters_last_submitted)
        self._parameters_backup = copy.deepcopy(self._parameters)
        self._plan_empty = False
        self._edit_mode = True
        self._plan_new = True
        self._update_widgets()

    def _pb_add_to_queue_clicked(self):
        self._parameters_last_submitted = copy.deepcopy(self._parameters)
        item = self._parameters_to_item(self._parameters)
        self.model.queue_item_add(item=item)
        # TODO: include validation of results (display error message/option to retry)
        self._edit_mode = False
        self._plan_new = False
        # Update the widget based on the currently selected item
        self.slot_view_item(self.model.selected_queue_item_uids)
        self._update_widgets()

    def _pb_save_clicked(self):
        self._parameters_last_submitted = copy.deepcopy(self._parameters)
        item = self._parameters_to_item(self._parameters, item_original=self._item_currently_loaded)
        self.model.queue_item_update(item=item)
        # TODO: include validation of results (display error message/option to retry)
        self._edit_mode = False
        self._plan_new = False
        # Update the widget based on the currently selected item
        self.slot_view_item(self.model.selected_queue_item_uids)
        self._update_widgets()

    def _pb_reset_clicked(self):
        self._parameters = copy.deepcopy(self._parameters_backup)
        self._update_widgets()

    def _pb_cancel_clicked(self):
        self._edit_mode = False
        self._plan_new = False
        self.slot_view_item(self.model.selected_queue_item_uids)

    def on_queue_item_selection_changed(self, event):
        sel_item_uids = event.selected_item_uids
        self.signal_update_selection.emit(sel_item_uids)

    def _item_to_parameters(self, item):
        # Simplified assumption that all arguments are kwargs
        item_params = item["kwargs"]

        parameters = dict()
        parameters["element"] = item_params.get("element", "")
        parameters["edge"] = item_params.get("edge", "")
        parameters["sample"] = item_params.get("sample", "")
        parameters["preparation"] = item_params.get("preparation", "")
        parameters["comment"] = item_params.get("comment", "")
        parameters["nscans"] = item_params.get("nscans", 1)
        start = item_params.get("start", "next")
        if start == "next":
            parameters["start_next"] = True
            parameters["start_number"] = 1
        else:
            parameters["start_next"] = False
            parameters["start_number"] = start
        parameters["mode"] = item_params.get("mode", "")

        parameters["filename"] = item_params.get("filename", "")

        bounds = item_params.get("bounds", "-200 200k")
        if isinstance(bounds, str):
            bounds = bounds.strip().split()
            parameters["bounds"] = [_.strip().lower() for _ in bounds]

        steps = item_params.get("steps", "1")
        if isinstance(steps, str):
            if steps.endswith("k"):
                steps = steps[:-1]
            steps = steps.strip().split(" ")
        else:
            steps = list(steps)
        parameters["steps"] = steps

        times = item_params.get("times", "1")
        if isinstance(times, str):
            times = times.strip().split(" ")
        else:
            times = list(times)
        parameters["times"] = times

        return parameters

    def _parameters_to_item(self, parameters, *, item_original=None):
        if item_original is None:
            item = {}
            kwargs = {}
        else:
            item = copy.deepcopy(item_original)
            kwargs = item.get("kwargs", {})

        kwargs["element"] = parameters["element"]
        kwargs["edge"] = parameters["edge"]
        kwargs["sample"] = parameters["sample"]
        kwargs["preparation"] = parameters["preparation"]
        kwargs["comment"] = parameters["comment"]
        kwargs["nscans"] = parameters["nscans"]
        kwargs["start"] = "next" if parameters["start_next"] else parameters["start_number"]
        kwargs["mode"] = parameters["mode"]
        kwargs["bounds"] = " ".join([f"{_}" for _ in parameters["bounds"]])
        kwargs["steps"] = " ".join([f"{_}" for _ in parameters["steps"]])
        kwargs["times"] = " ".join([f"{_}" for _ in parameters["times"]])

        filename = parameters["filename"]
        # Don't include filename parameter if it is an empty string
        if filename:
            kwargs["filename"] = filename

        # The following parameters we don't set in the form, but they are needed for the plan to run.
        if "snapshots" not in kwargs:
            kwargs["snapshots"] = False
        if "htmlpage" not in kwargs:
            kwargs["htmlpage"] = False
        if "lims" not in kwargs:
            kwargs["lims"] = False

        item.update({"item_type": "plan", "name": "xafs", "args": [], "kwargs": kwargs})
        return item

    @Slot(object)
    def slot_view_item(self, sel_item_uids):
        # If the widget is in edit mode, then ignore selection change
        if self._edit_mode:
            return

        # The viewer is blank if more than 1 item is selected.
        if len(sel_item_uids) == 1:
            sel_item_uid = sel_item_uids[0]
            sel_item_pos = self.model.queue_item_uid_to_pos(sel_item_uid)

            if sel_item_pos >= 0:
                item = copy.deepcopy(self.model._plan_queue_items[sel_item_pos])
                item_name = item.get("name", "")
            else:
                item, item_name = None, ""
        else:
            item, item_name = None, ""

        self._item_currently_loaded = copy.deepcopy(item)

        # View only plans named 'xafs'
        if item_name in ("xafs",):
            self._parameters = self._item_to_parameters(item)
            self._plan_empty = False
            self._edit_mode = False
            self._plan_new = False
            self._update_widgets()
        else:
            self._parameters = {}
            self._plan_empty = True
            self._edit_mode = False
            self._plan_new = False
            self._update_widgets()

    def on_update_widgets(self, event):
        self.signal_update_widgets.emit()

    @Slot()
    def slot_update_widgets(self):
        self._update_widget_state()
