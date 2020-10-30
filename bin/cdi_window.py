# #########################################################################
# Copyright (c) , UChicago Argonne, LLC. All rights reserved.             #
#                                                                         #
# See LICENSE file.                                                       #
# #########################################################################

"""
This is GUI that allows user to configure and run experiment.
"""

__author__ = "Barbara Frosik"
__copyright__ = "Copyright (c), UChicago Argonne, LLC."
__docformat__ = 'restructuredtext en'
__all__ = ['select_file',
           'select_dir',
           'msg_window',
           'main']

import sys
import os
import shutil
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import importlib
#import format_data as run_dt
#import run_rec as run_rc
#import run_disp as run_dp
#import run_prep_34idc as prep
import reccdi.src_py.utilities.utils as ut
import reccdi.src_py.utilities.parse_ver as ver
#import reccdi.src_py.beamlines.aps_34id.spec as spec
import reccdi.src_py.beamlines.aps_34id.diffractometer as dif
import reccdi.src_py.beamlines.aps_34id.detectors as det

def select_file(start_dir):
    """
    Shows dialog interface allowing user to select file from file system.

    Parameters
    ----------
    start_dir : str
        directory where to start selecting the file

    Returns
    -------
    str
        name of selected file or None
    """
    dialog = QFileDialog(None, 'select dir', start_dir)
    dialog.setFileMode(QFileDialog.ExistingFile)
    dialog.setSidebarUrls([QUrl.fromLocalFile(start_dir)])
    if dialog.exec_() == QDialog.Accepted:
        return str(dialog.selectedFiles()[0])
    else:
        return None


def select_dir(start_dir):
    """
    Shows dialog interface allowing user to select directory from file system.

    Parameters
    ----------
    start_dir : str
        directory where to start selecting

    Returns
    -------
    str
        name of selected directory or None
    """
    dialog = QFileDialog(None, 'select dir', start_dir)
    dialog.setFileMode(QFileDialog.DirectoryOnly)
    dialog.setSidebarUrls([QUrl.fromLocalFile(start_dir)])
    if dialog.exec_() == QDialog.Accepted:
        return str(dialog.selectedFiles()[0])
    else:
        return None


def msg_window(text):
    """
    Shows message with requested information (text)).

    Parameters
    ----------
    text : str
        string that will show on the screen

    Returns
    -------
    noting
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(text)
    msg.setWindowTitle("Info")
    msg.exec_()


class cdi_gui(QWidget):
    def __init__(self, parent=None):
        """
        Constructor, initializes GUI.

        Parameters
        ----------
        none

        Returns
        -------
        noting
        """
        super(cdi_gui, self).__init__(parent)
        self.exp_id = None
        self.experiment_dir = None
        self.working_dir = None
        self.specfile = None
        uplayout = QFormLayout()

        self.set_work_dir_button = QPushButton()
        uplayout.addRow("Working Directory", self.set_work_dir_button)
        self.Id_widget = QLineEdit()
        uplayout.addRow("Experiment ID", self.Id_widget)
        self.scan_widget = QLineEdit()
        uplayout.addRow("scan(s)", self.scan_widget)
        self.spec_file_button = QPushButton()
        uplayout.addRow("spec file", self.spec_file_button)

        vbox = QVBoxLayout()
        vbox.addLayout(uplayout)

        self.t = cdi_conf_tab(self)
        vbox.addWidget(self.t)

        downlayout = QFormLayout()
        self.set_conf_from_button = QPushButton("Load conf from")
        self.set_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        downlayout.addWidget(self.set_conf_from_button)
        self.create_exp_button = QPushButton('set experiment')
        self.create_exp_button.setStyleSheet("background-color:rgb(120,180,220)")
        downlayout.addWidget(self.create_exp_button)
        self.run_button = QPushButton('run everything', self)
        self.run_button.setStyleSheet("background-color:rgb(175,208,156)")
        downlayout.addWidget(self.run_button)
        vbox.addLayout(downlayout)

        self.setLayout(vbox)
        self.setWindowTitle("CDI Reconstruction")

        self.set_conf_from_button.clicked.connect(self.load_conf_dir)
        self.set_work_dir_button.clicked.connect(self.set_working_dir)
        self.spec_file_button.clicked.connect(self.set_spec_file)
        self.run_button.clicked.connect(self.run_everything)
        self.create_exp_button.clicked.connect(self.set_experiment)


    def set_spec_file(self):
        """
        Calls selection dialog. The selected spec file is parsed.
        The specfile is saved in config.

        Parameters
        ----------
        none

        Returns
        -------
        noting
        """
        self.specfile = select_file(os.getcwd())
        if self.specfile is not None:
            self.spec_file_button.setStyleSheet("Text-align:left")
            self.spec_file_button.setText(self.specfile)
            self.t.parse_spec()
        else:
            self.specfile = None
            self.spec_file_button.setText('')
        if self.is_exp_exists() or self.is_exp_set():
            self.set_experiment()


    def run_everything(self):
        """
        Runs everything.py user script in bin directory.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        if not self.is_exp_exists():
            msg_window('the experiment has not been created yet')
        elif not self.is_exp_set():
            msg_window('the experiment has changed, pres "set experiment" button')
        else:
            self.t.prepare()
            self.t.format_data()
            self.t.reconstruction()
            self.t.display()


    def is_exp_exists(self):
        """
        Determines if minimum information for creating the experiment space exists, i.e the working directory and experiment id must be set.
        Resolves the experiment name, and create experiment directory if it does not exist.

        Parameters
        ----------
        none

        Returns
        -------
        boolean
            True if experiment exists, False otherwise
        """
        if self.exp_id is None:
            return False
        if self.working_dir is None:
            return False
        exp_id = str(self.Id_widget.text()).strip()
        scan = str(self.scan_widget.text()).strip()
        if scan != '':
            exp_id = exp_id + '_' + scan
        if not os.path.exists(os.path.join(self.working_dir, exp_id)):
            return False
        return True


    def is_exp_set(self):
        """
        The GUI can be used to load an experiment, and then change the parameters, such id or scan. This function will return True if information in class are the same as in the GUI.

        Parameters
        ----------
        none

        Returns
        -------
        boolean
            True if experiment has been set, False otherwise
        """
        if self.exp_id is None:
            return False
        if self.working_dir is None:
            return False
        if self.id != str(self.Id_widget.text()).strip():
            return False
        if self.scan != str(self.scan_widget.text()).strip():
            return False
        return True


    def load_conf_dir(self):
        """
        It shows the select dialog for user to select directory to load configuration from configuration files in that directory. If no configuration files are found user will see info message.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        load_dir = select_dir(os.getcwd())
        missing = 0
        if load_dir is not None:
            # load the experiment info only if no id is entered
            if os.path.isfile(os.path.join(load_dir, 'config')) and str(self.Id_widget.text()).strip() == '':
                self.load_main(load_dir)
            else:
                missing += 1
            conf_prep_file = os.path.join(load_dir, 'config_prep')
            if os.path.isfile(conf_prep_file):
                self.t.load_prep_tab(conf_prep_file)
            else:
                missing += 1
            conf_data_file = os.path.join(load_dir, 'config_data')
            if os.path.isfile(conf_data_file):
                self.t.load_data_tab(conf_data_file)
            else:
                missing += 1
            conf_rec_file = os.path.join(load_dir, 'config_rec')
            if os.path.isfile(conf_rec_file):
                self.t.load_rec_tab(conf_rec_file)
            else:
                missing += 1
            conf_disp_file = os.path.join(load_dir, 'config_disp')
            if os.path.isfile(conf_disp_file):
                self.t.load_disp_tab(conf_disp_file)
            else:
                missing += 1
            if missing == 5:
                msg_window('info: no configuration file found in load directory')
            else:
                self.set_conf_from_button.setStyleSheet("Text-align:left")
                self.set_conf_from_button.setText('config loaded')
                self.set_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        else:
            msg_window('please select valid conf directory')


    def set_working_dir(self):
        """
        It shows the select dialog for user to select working directory. If the selected directory does not exist user will see info message.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.working_dir = select_dir(os.getcwd())
        if self.working_dir is not None:
            self.set_work_dir_button.setStyleSheet("Text-align:left")
            self.set_work_dir_button.setText(self.working_dir)
        else:
            self.set_work_dir_button.setText('')
            msg_window('please select valid working directory')
            return


    def load_main(self, load_dir):
        """
        It reads 'config' file from the given directory, parses all parameters, verifies, and sets the display in window and class members to parsed values.

        Parameters
        ----------
        load_dir : str
            a directory to load the main configuration from

        Returns
        -------
        nothing
        """
        conf = os.path.join(load_dir, 'config')
        try:
            conf_map = ut.read_config(conf)
        except Exception:
            msg_window('please check configuration file ' + conf + '. Cannot parse, ')
            return

        try:
            working_dir = conf_map.working_dir
            if not os.path.isdir(working_dir):
                self.working_dir = None
                self.set_work_dir_button.setText('')
                msg_window('The working directory ' + working_dir + ' from config file does not exist. Select valid working directory and set experiment')
            else:
                self.working_dir = conf_map.working_dir
                self.set_work_dir_button.setStyleSheet("Text-align:left")
                self.set_work_dir_button.setText(self.working_dir)
        except:
            pass

        try:
            self.scan = conf_map.scan
            self.scan_widget.setText(self.scan)
        except:
            self.scan = None

        try:
            self.id = conf_map.experiment_id
            self.Id_widget.setText(self.id)
            if self.scan != None:
                self.exp_id = self.id + '_' + self.scan
            else:
                self.exp_id = self.id
            self.experiment_dir = os.path.join(self.working_dir, self.exp_id)
        except:
            pass

        try:
            specfile = conf_map.specfile
            if os.isfile(specfile):
                self.specfile = conf_map.specfile
                self.spec_file_button.setStyleSheet("Text-align:left")
                self.spec_file_button.setText(self.specfile)
                self.t.parse_spec()
            else:
                msg_window('The specfile file ' + specfile + ' in config file does not exist')
        except:
            self.specfile = None
            self.spec_file_button.setText('')

        if self.experiment_dir is not None:
            # this shows default results directory in display tab
            self.t.results_dir = os.path.join(self.experiment_dir, 'results')
            self.t.result_dir_button.setStyleSheet("Text-align:left")
            self.t.result_dir_button.setText(self.t.results_dir)
            self.update_rec_configs_choice()


    def update_rec_configs_choice(self):
        """
        Looks for alternate reconstruction configurations, and updates window with that information.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        # this will update the configuration choices in reconstruction tab
        # fill out the config_id choice bar by reading configuration files names
        rec_ids = []
        for file in os.listdir(os.path.join(self.experiment_dir, 'conf')):
            if file.endswith('_config_rec'):
                rec_ids.append(file[0:len(file)-len('_config_rec')])
        if len(rec_ids) > 0:
            self.t.rec_id.addItems(rec_ids)
            self.t.rec_id.show()


    def assure_experiment_dir(self):
        """
        It creates experiment directory, and experiment configuration directory if they dp not exist.

        Parameters
        ----------
        nothing

        Returns
        -------
        nothing
        """
        if not os.path.exists(self.experiment_dir):
            os.makedirs(self.experiment_dir)
        experiment_conf_dir = os.path.join(self.experiment_dir, 'conf')
        if not os.path.exists(experiment_conf_dir):
            os.makedirs(experiment_conf_dir)
        else:
            self.update_rec_configs_choice()


    def set_experiment(self):
        """
        Reads the parameters in the window, and sets the experiment to this values, i.e. creates experiment directory, and saves all configuration files with parameters from window.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.id = str(self.Id_widget.text()).strip()
        if self.id == '' or self.working_dir is None:
            msg_window('id and working directory must be entered')
            return
        conf_map = {}

        self.scan = str(self.scan_widget.text()).strip()
        if len(self.scan) > 0:
            scans = self.scan.split('-')
            if len(scans) > 2:
                msg_window('if entering scan or scan range, please enter numeric values, separated with "-" if range')
                return
            for sc in scans:
                try:
                    numeric = int(sc)
                except:
                    msg_window('if entering scan or scan range, please enter numeric values, separated with "-" if range')
                    return
            conf_map['scan'] = '"' + self.scan + '"'
            self.exp_id = self.id + '_' + self.scan
        else:
            self.exp_id = self.id
        self.experiment_dir = os.path.join(self.working_dir, self.exp_id)
        self.assure_experiment_dir()

        # read the configurations from GUI and write to experiment config files
        # save the main config
        conf_map['working_dir'] = '"' + str(self.working_dir).strip() + '"'
        conf_map['experiment_id'] = '"' + self.id + '"'
        if self.specfile is not None:
            conf_map['specfile'] = '"' + str(self.specfile).strip() + '"'
        self.write_conf(conf_map, os.path.join(self.experiment_dir, 'conf'), 'config')

        # save prep config
        conf_map = self.t.get_prep_config()
        if len(conf_map) > 0:
            self.write_conf(conf_map, os.path.join(self.experiment_dir, 'conf'), 'config_prep')

        # save data config
        conf_map = self.t.get_data_config()
        if len(conf_map) > 0:
            self.write_conf(conf_map, os.path.join(self.experiment_dir, 'conf'), 'config_data')

        # save rec config
        conf_map = self.t.get_rec_config()
        if len(conf_map) > 0:
            self.write_conf(conf_map, os.path.join(self.experiment_dir, 'conf'), 'config_rec')

        # save disp config
        conf_map = self.t.get_disp_config()
        if len(conf_map) > 0:
            self.write_conf(conf_map, os.path.join(self.experiment_dir, 'conf'), 'config_disp')

        # this shows default results directory in display window
        self.t.results_dir = os.path.join(self.experiment_dir, 'results')
        self.t.result_dir_button.setStyleSheet("Text-align:left")
        self.t.result_dir_button.setText(self.t.results_dir)


    def write_conf(self, conf_map, dir, file):
        """
        It creates configuration file from the parameters included in dictionary, verifies, and saves in the configuration directory.

        Parameters
        ----------
        conf_map : dict
            dictionary containing configuration parameters
        dir : str
            a directory where the configuration file will be saved
        file : str
            name of the configuration file to save

        Returns
        -------
        nothing
        """
        # create "temp" file first, verify it, and if ok, copy to a configuration file
        if not os.path.exists(dir):
            os.makedirs(dir)
        conf_file = os.path.join(dir, file)
        temp_file = os.path.join(dir, 'temp')
        with open(temp_file, 'a') as f:
            for key in conf_map:
                value = conf_map[key]
                if len(value) > 0:
                    f.write(key + ' = ' + conf_map[key] + '\n')
        f.close()

        if file == 'config':
            if not ver.ver_config(temp_file):
                os.remove(temp_file)
                msg_window('please check the entries in the main window. Cannot save this format')
                return False
        elif file == 'config_prep':
            if not ver.ver_config_prep(temp_file):
                os.remove(temp_file)
                msg_window('please check the entries in the Data prep tab. Cannot save this format')
                return False
        elif file == 'config_data':
            if not ver.ver_config_data(temp_file):
                os.remove(temp_file)
                msg_window('please check the entries in the Data tab. Cannot save this format')
                return False
        elif file.endswith('config_rec'):
            if not ver.ver_config_rec(temp_file):
                os.remove(temp_file)
                msg_window('please check the entries in the Reconstruction tab. Cannot save this format')
                return False
        elif file == 'config_disp':
            if not ver.ver_config_disp(temp_file):
                os.remove(temp_file)
                msg_window('please check the entries in the Display tab. Cannot save this format')
                return False
        # copy if verified
        shutil.copy(temp_file, conf_file)
        os.remove(temp_file)
        return True

class cdi_conf_tab(QTabWidget):
    """
    The main window contains four tabs, each tab holding parameters for different part of processing. The tabs are as follows: prep (prepare data), data (format data), rec (reconstruction), disp (visualization). This class holds holds the tabs.
    """
    def __init__(self, main_win, parent=None):
        """
        Constructor, initializes the tabs.
        """
        super(cdi_conf_tab, self).__init__(parent)
        self.main_win = main_win
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()

        self.data_dir = None
        self.darkfield_filename = None
        self.whitefield_filename = None
        self.binning = None
        self.results_dir = None
        self.addTab(self.tab1, "Data prep")
        self.addTab(self.tab2, "Data")
        self.addTab(self.tab3, "Reconstruction")
        self.addTab(self.tab4, "Display")
        self.tab1UI()
        self.tab2UI()
        self.tab3UI()
        self.tab4UI()


    def tab1UI(self):
        """
        Creates and initializes the 'prep' tab.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.script = None
        self.imported_script = False
        layout = QFormLayout()
        self.separate_scans = QCheckBox()
        layout.addRow("separate scans", self.separate_scans)
        self.separate_scans.setChecked(False)
        self.data_dir_button = QPushButton()
        layout.addRow("data directory", self.data_dir_button)
        self.dark_file_button = QPushButton()
        layout.addRow("darkfield file", self.dark_file_button)
        self.white_file_button = QPushButton()
        layout.addRow("whitefield file", self.white_file_button)
        self.roi = QLineEdit()
        layout.addRow("detector area (roi)", self.roi)
        self.min_files = QLineEdit()
        layout.addRow("min files in scan", self.min_files)
        self.exclude_scans = QLineEdit()
        layout.addRow("exclude scans", self.exclude_scans)
        self.prep = QComboBox()
        self.prep.addItem("34ID prep")
        self.prep.addItem("custom")
        self.prep.addItem("copy from")
        layout.addRow("choose data preparation ", self.prep)
        # add sub-layout with rows that apply to the choice form above
        sub_layout = QFormLayout()
        self.load_prep(sub_layout)
        layout.addRow(sub_layout)
        self.set_prep_conf_from_button = QPushButton("Load prep conf from")
        self.set_prep_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        #layout.addWidget(self.set_prep_conf_from_button)
        self.prep_button = QPushButton('prepare', self)
        self.prep_button.setStyleSheet("background-color:rgb(175,208,156)")
        #layout.addWidget(self.prep_button)
        layout.addRow(self.set_prep_conf_from_button, self.prep_button)
        self.tab1.setLayout(layout)

        self.prep_button.clicked.connect(self.prepare)
        self.prep.currentIndexChanged.connect(lambda: self.load_prep(sub_layout))
        self.data_dir_button.clicked.connect(self.set_data_dir)
        self.dark_file_button.clicked.connect(self.set_dark_file)
        self.white_file_button.clicked.connect(self.set_white_file)
        self.set_prep_conf_from_button.clicked.connect(self.load_prep_conf)


    def load_prep(self, layout):
        """
        Loads additional fields in the 'prep' tab when the prep type selected is different than 34-IDC.

        Parameters
        ----------
        layout : QFormLayout
            layout to add the wigets

        Returns
        -------
        nothing
        """
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()

        if str(self.prep.currentText()) == "custom":
            self.script_button = QPushButton()
            layout.addRow("select script", self.script_button)
            self.prep_exec = QLineEdit()
            layout.addRow("prep function", self.prep_exec)
            self.args = QLineEdit()
            layout.addRow("arguments (str/num)", self.args)
            self.script_button.clicked.connect(self.set_prep_script)

        elif str(self.prep.currentText()) == "copy from":
            self.ready_prep = QPushButton()
            layout.addRow("prep file", self.ready_prep)
            self.ready_prep.clicked.connect(self.set_prep_file)


    def tab2UI(self):
        """
        Creates and initializes the 'data' tab.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        layout = QFormLayout()
        self.aliens = QLineEdit()
        layout.addRow("aliens", self.aliens)
        self.amp_intensity = QLineEdit()
        layout.addRow("amp intensity", self.amp_intensity)
        self.center_shift = QLineEdit()
        layout.addRow("center_shift", self.center_shift)
        self.adjust_dimensions = QLineEdit()
        layout.addRow("pad, crop", self.adjust_dimensions)
        self.binning = QLineEdit()
        layout.addRow("binning", self.binning)
        self.set_data_conf_from_button = QPushButton("Load data conf from")
        self.set_data_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        #layout.addRow(self.set_data_conf_from_button)
        self.config_data_button = QPushButton('format data', self)
        self.config_data_button.setStyleSheet("background-color:rgb(175,208,156)")
        #layout.addRow(self.config_data_button)
        layout.addRow(self.set_data_conf_from_button, self.config_data_button)
        self.tab2.setLayout(layout)

        # this will create config_data file and run data script
        # to generate data ready for reconstruction
        self.config_data_button.clicked.connect(self.format_data)
        self.set_data_conf_from_button.clicked.connect(self.load_data_conf)


    def tab3UI(self):
        """
        Creates and initializes the 'reconstruction' tab.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.mult_rec_conf = False
        self.old_conf_id = ''
        layout = QVBoxLayout()
        ulayout = QFormLayout()
        mlayout = QHBoxLayout()
        self.add_conf_button = QPushButton('add configuration', self)
        ulayout.addWidget(self.add_conf_button)
        self.rec_id = QComboBox()
        self.rec_id.InsertAtBottom
        self.rec_id.addItem("")
        ulayout.addWidget(self.rec_id)
        self.rec_id.hide()
        self.proc = QComboBox()
        self.proc.addItem("cuda")
        self.proc.addItem("opencl")
        self.proc.addItem("cpu")
        ulayout.addRow("processor type", self.proc)
        self.cont = QCheckBox()
        ulayout.addRow("continuation", self.cont)
        self.cont.setChecked(False)
        self.device = QLineEdit()
        ulayout.addRow("device(s)", self.device)
        self.reconstructions = QLineEdit()
        ulayout.addRow("number of reconstructions", self.reconstructions)
        self.alg_seq = QLineEdit()
        ulayout.addRow("algorithm sequence", self.alg_seq)
        # TODO add logic to show this only if HIO is in sequence
        self.beta = QLineEdit()
        ulayout.addRow("beta", self.beta)
        self.rec_default_button = QPushButton('set to defaults', self)
        ulayout.addWidget(self.rec_default_button)

        llayout = QFormLayout()
        self.set_rec_conf_from_button = QPushButton("Load rec conf from")
        self.set_rec_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        #layout.addWidget(self.set_rec_conf_from_button)
        self.features = Features(self, mlayout)
        self.config_rec_button = QPushButton('run reconstruction', self)
        self.config_rec_button.setStyleSheet("background-color:rgb(175,208,156)")
        #layout.addWidget(self.config_rec_button)
        llayout.addRow(self.set_rec_conf_from_button, self.config_rec_button)
        spacer = QSpacerItem(0,3)
        llayout.addItem(spacer)

        layout.addLayout(ulayout)
        layout.addLayout(mlayout)
        layout.addLayout(llayout)

        self.tab3.setAutoFillBackground(True)
        self.tab3.setLayout(layout)

        self.config_rec_button.clicked.connect(self.reconstruction)
        self.cont.stateChanged.connect(lambda: self.toggle_cont(ulayout))
        self.rec_default_button.clicked.connect(self.rec_default)
        self.add_conf_button.clicked.connect(self.add_rec_conf)
        self.rec_id.currentIndexChanged.connect(self.toggle_conf)
        self.set_rec_conf_from_button.clicked.connect(self.load_rec_conf_dir)


    def toggle_cont(self, layout):
        """
        Invoked when the 'cont' checkbox is selected, indicating this reconstruction is continuation.

        Parameters
        ----------
        layout : QFormLayout
            a layout to add the continue dir
            
        Returns
        -------
        nothing
        """
        cb_label = layout.labelForField(self.cont)
        if self.cont.isChecked():
            self.cont_dir = QLineEdit()
            layout.insertRow(2, "continue dir", self.cont_dir)
            cb_label.setStyleSheet('color: black')
        else:
            cb_label.setStyleSheet('color: grey')


    def add_rec_conf(self):
        id, ok = QInputDialog.getText(self, '',"enter configuration id")
        if ok and len(id) > 0:
            if self.mult_rec_conf:
                self.rec_id.addItem(id)
            else:
                self.mult_rec_conf = True
                self.rec_id.show()
                self.rec_id.addItem(id)
            #self.rec_id.setCurrentIndex(self.rec_id.count()-1)

        # copy the config_rec into <id>_config_rec and show the
        conf_file = os.path.join(self.main_win.experiment_dir, 'conf', 'config_rec')
        new_conf_file = os.path.join(self.main_win.experiment_dir, 'conf', id + '_config_rec')
        shutil.copyfile(conf_file, new_conf_file)
        self.rec_id.setCurrentIndex(self.rec_id.count()-1)


    def toggle_conf(self):
        """
        Invoked when the configuration to use in the reconstruction was changed, i.e. alternate config was selected or main. This will bring the parameters from the previous config to be saved, and the new ones retrieved and showed in window.

        Parameters
        ----------
        layout : QFormLayout
            a layout to add the continue dir
            
        Returns
        -------
        nothing
        """
        # save the configuration file before updating the incoming config
        if self.old_conf_id == '':
            conf_file = 'config_rec'
        else:
            conf_file = self.old_conf_id + '_config_rec'

        conf_map = self.get_rec_config()
        conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')

        if self.main_win.write_conf(conf_map, conf_dir, conf_file):
            self.old_conf_id = str(self.rec_id.currentText())
        else:
            msg_window('configuration  ' + conf_file + ' was not saved')
        # if a config file corresponding to the rec id exists, load it
        # otherwise read from base configuration and load
        if self.old_conf_id == '':
            conf_file = os.path.join(conf_dir, 'config_rec')
        else:
            conf_file = os.path.join(conf_dir, self.old_conf_id + '_config_rec')

        if os.path.isfile(conf_file):
            self.load_rec_tab(conf_file)
        else:
            self.load_rec_tab(os.path.join(conf_dir, 'config_rec'))


    def tab4UI(self):
        """
        Creates and initializes the 'disp' tab.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        layout = QFormLayout()
        self.result_dir_button = QPushButton()
        layout.addRow("results directory", self.result_dir_button)
        self.diffractometer = QLineEdit()
        layout.addRow("diffractometer", self.diffractometer)
        self.crop = QLineEdit()
        layout.addRow("crop", self.crop)
        self.rampups = QLineEdit()
        layout.addRow("ramp upscale", self.rampups)
        self.energy = QLineEdit()
        layout.addRow("energy", self.energy)
        self.delta = QLineEdit()
        layout.addRow("delta (deg)", self.delta)
        self.gamma = QLineEdit()
        layout.addRow("gamma (deg)", self.gamma)
        self.detdist = QLineEdit()
        layout.addRow("detdist (mm)", self.detdist)
        self.theta = QLineEdit()
        layout.addRow("theta (deg)", self.theta)
        self.chi = QLineEdit()
        layout.addRow("chi (deg)", self.chi)
        self.phi = QLineEdit()
        layout.addRow("phi (deg)", self.phi)
        self.scanmot = QLineEdit()
        layout.addRow("scan motor", self.scanmot)
        self.scanmot_del = QLineEdit()
        layout.addRow("scan motor delay", self.scanmot_del)
        self.detector = QLineEdit()
        layout.addRow("detector", self.detector)
        self.set_disp_conf_from_button = QPushButton("Load disp conf from")
        self.set_disp_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        #layout.addRow(self.set_disp_conf_from_button)
        self.config_disp = QPushButton('process display', self)
        self.config_disp.setStyleSheet("background-color:rgb(175,208,156)")
        #layout.addRow(self.config_disp)
        layout.addRow(self.set_disp_conf_from_button, self.config_disp)
        self.tab4.setLayout(layout)

        self.result_dir_button.clicked.connect(self.set_results_dir)
        self.config_disp.clicked.connect(self.display)
        self.energy.textChanged.connect(lambda: self.set_overriden(self.energy))
        self.delta.textChanged.connect(lambda: self.set_overriden(self.delta))
        self.gamma.textChanged.connect(lambda: self.set_overriden(self.gamma))
        self.detdist.textChanged.connect(lambda: self.set_overriden(self.detdist))
        self.theta.textChanged.connect(lambda: self.set_overriden(self.theta))
        self.chi.textChanged.connect(lambda: self.set_overriden(self.chi))
        self.phi.textChanged.connect(lambda: self.set_overriden(self.phi))
        self.scanmot.textChanged.connect(lambda: self.set_overriden(self.scanmot))
        self.scanmot_del.textChanged.connect(lambda: self.set_overriden(self.scanmot_del))
        self.detector.textChanged.connect(lambda: self.set_overriden(self.detector))
        self.set_disp_conf_from_button.clicked.connect(self.load_disp_conf)
        self.layout4 = layout


    def load_prep_tab(self, conf):
        """
        It verifies given configuration file, reads the parameters, and fills out the window.

        Parameters
        ----------
        conf : str
            configuration file (config_prep)

        Returns
        -------
        nothing
        """
        if not os.path.isfile(conf):
            msg_window('info: the load directory does not contain config_prep file')
            return
        if not ver.ver_config_prep(conf):
            msg_window('please check configuration file ' + conf + '. Cannot parse, ')
            return
        try:
            conf_map = ut.read_config(conf)
        except Exception as e:
            msg_window('please check configuration file ' + conf + '. Cannot parse, ' + str(e))
            return

        try:
            separate_scans = conf_map.separate_scans
            if separate_scans:
                self.separate_scans.setChecked(True)
        except:
            pass
        try:
            data_dir = conf_map.data_dir
            if os.path.isdir(data_dir):
                self.data_dir = conf_map.data_dir
                self.data_dir_button.setStyleSheet("Text-align:left")
                self.data_dir_button.setText(self.data_dir)
            else:
                msg_window('The data_dir directory in config_prep file  ' + data_dir + ' does not exist')
        except:
            self.data_dir = None
            self.data_dir_button.setText('')
        try:
            darkfield_filename = conf_map.darkfield_filename
            if os.isfile(darkfield_filename):
                self.darkfield_filename = conf_map.darkfield_filename
                self.dark_file_button.setStyleSheet("Text-align:left")
                self.dark_file_button.setText(self.darkfield_filename)
            else:
                msg_window('The darkfield file ' + darkfield_filename + ' in config_prep file does not exist')
        except:
            self.darkfield_filename = None
            self.dark_file_button.setText('')
        try:
            whitefield_filename = conf_map.whitefield_filename
            if os.isfile(whitefield_filename):
                self.whitefield_filename = conf_map.whitefield_filename
                self.white_file_button.setStyleSheet("Text-align:left")
                self.white_file_button.setText(self.whitefield_filename)
            else:
                msg_window('The whitefield file ' + whitefield_filename + ' in config_prep file does not exist')
        except:
            self.whitefield_filename = None
            self.white_file_button.setText('')
        try:
            self.min_files.setText(str(conf_map.min_files).replace(" ", ""))
        except:
            pass
        try:
            self.exclude_scans.setText(str(conf_map.exclude_scans).replace(" ", ""))
        except:
            pass
        try:
            self.roi.setText(str(conf_map.roi).replace(" ", ""))
        except:
            pass
        prep_file = None
        try:
            prep_file = conf_map.prep_file
        except:
            pass
        if prep_file is not None:
            self.prep.setCurrentIndex(2)
            self.ready_prep.setStyleSheet("Text-align:left")
            self.ready_prep.setText(prep_file)


    def load_data_tab(self, conf):
        """
        It verifies given configuration file, reads the parameters, and fills out the window.

        Parameters
        ----------
        conf : str
            configuration file (config_data)

        Returns
        -------
        nothing
        """
        if not os.path.isfile(conf):
            msg_window('info: the load directory does not contain config_data file')
            return
        if not ver.ver_config_data(conf):
            msg_window('please check configuration file ' + conf + '. Cannot parse, ')
            return
        try:
            conf_map = ut.read_config(conf)
        except Exception as e:
            msg_window('please check configuration file ' + conf + '. Cannot parse, ' + str(e))
            return

        try:
            self.aliens.setText(str(conf_map.aliens).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.amp_intensity.setText(str(conf_map.amp_threshold).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.binning.setText(str(conf_map.binning).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.center_shift.setText(str(conf_map.center_shift).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.adjust_dimensions.setText(str(conf_map.adjust_dimensions).replace(" ", ""))
        except AttributeError:
            pass


    def load_rec_tab(self, conf):
        """
        It verifies given configuration file, reads the parameters, and fills out the window.

        Parameters
        ----------
        conf : str
            configuration file (config_rec)

        Returns
        -------
        nothing
        """
        if not os.path.isfile(conf):
            msg_window('info: the load directory does not contain config_rec file')
            return
        if not ver.ver_config_rec(conf):
            msg_window('please check configuration file ' + conf + '. Cannot parse, ')
            return
        try:
            conf_map = ut.read_config(conf)
        except Exception as e:
            msg_window('please check configuration file ' + conf + '. Cannot parse, ' + str(e))
            return

        try:
            self.device.setText(str(conf_map.device).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.reconstructions.setText(str(conf_map.reconstructions).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.alg_seq.setText(str(conf_map.algorithm_sequence).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.beta.setText(str(conf_map.beta).replace(" ", ""))
        except AttributeError:
            pass

        for feat_id in self.features.feature_dir:
            self.features.feature_dir[feat_id].init_config(conf_map)

        # set the results_dir in display tab
        if self.main_win.is_exp_exists() and self.main_win.is_exp_set() :
            self.init_results_dir()


    def load_disp_tab(self, conf):
        """
        It verifies given configuration file, reads the parameters, and fills out the window.

        Parameters
        ----------
        conf : str
            configuration file (config_disp)

        Returns
        -------
        nothing
        """
        if not os.path.isfile(conf):
            msg_window('info: the load directory does not contain config_disp file')
            return
        if not ver.ver_config_data(conf):
            msg_window('please check configuration file ' + conf + '. Cannot parse, ')
            return
        try:
            conf_map = ut.read_config(conf)
        except Exception as e:
            msg_window('please check configuration file ' + conf + '. Cannot parse, ' + str(e))
            return
        # if parameters are configured, override the readings from spec file
        try:
            self.diffractometer.setText(str(conf_map.diffractometer).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.crop.setText(str(conf_map.crop).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.rampups.setText(str(conf_map.rampups).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.energy.setText(str(conf_map.energy).replace(" ", ""))
            self.energy.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.delta.setText(str(conf_map.delta).replace(" ", ""))
            self.delta.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.gamma.setText(str(conf_map.gamma).replace(" ", ""))
            self.gamma.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.detdist.setText(str(conf_map.detdist).replace(" ", ""))
            self.detdist.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.theta.setText(str(conf_map.theta).replace(" ", ""))
            self.theta.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.chi.setText(str(conf_map.chi).replace(" ", ""))
            self.chi.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.phi.setText(str(conf_map.phi).replace(" ", ""))
            self.phi.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.scanmot.setText(str(conf_map.scanmot).replace(" ", ""))
            self.scanmot.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.scanmot_del.setText(str(conf_map.scanmot_del).replace(" ", ""))
            self.scanmot_del.setStyleSheet('color: black')
        except AttributeError:
            pass
        try:
            self.detector.setText(str(conf_map.detector).replace(" ", ""))
            self.detector.setStyleSheet('color: black')
        except AttributeError:
            pass


    def get_prep_config(self):
        """
        It reads parameters related to preparation from the window and adds them to dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        conf_map : dict
            contains parameters read from window
        """
        conf_map = {}
        if self.data_dir is not None:
            conf_map['data_dir'] = '"' + str(self.data_dir).strip() + '"'
        if self.darkfield_filename is not None:
            conf_map['darkfield_filename'] = '"' + str(self.darkfield_filename).strip() + '"'
        if self.whitefield_filename is not None:
            conf_map['whitefield_filename'] = '"' + str(self.whitefield_filename).strip() + '"'
        if self.separate_scans.isChecked():
            conf_map['separate_scans'] = 'true'
        if len(self.min_files.text()) > 0:
            min_files = str(self.min_files.text())
            conf_map['min_files'] = min_files
        if len(self.exclude_scans.text()) > 0:
            conf_map['exclude_scans'] = str(self.exclude_scans.text()).replace('\n','')
        if len(self.roi.text()) > 0:
            roi = str(self.roi.text())
            conf_map['roi'] = roi
        try:
            if str(self.ready_prep.text()) != '':
                conf_map['prep_file'] = '"' + str(self.prep_file) + '"'
        except:
            pass

        return conf_map


    def get_data_config(self):
        """
        It reads parameters related to formatting data from the window and adds them to dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        conf_map : dict
            contains parameters read from window
        """
        conf_map = {}
        if len(self.aliens.text()) > 0:
            if os.path.isfile(str(self.aliens.text()).strip()):
                conf_map['aliens'] = '"' + str(self.aliens.text()) + '"'
            else:
                conf_map['aliens'] = str(self.aliens.text()).replace('\n', '')
        if len(self.amp_intensity.text()) > 0:
            conf_map['amp_threshold'] = str(self.amp_intensity.text())
        if len(self.binning.text()) > 0:
            conf_map['binning'] = str(self.binning.text()).replace('\n', '')
        if len(self.center_shift.text()) > 0:
            conf_map['center_shift'] = str(self.center_shift.text()).replace('\n', '')
        if len(self.adjust_dimensions.text()) > 0:
            conf_map['adjust_dimensions'] = str(self.adjust_dimensions.text()).replace('\n', '')

        return conf_map


    def get_rec_config(self):
        """
        It reads parameters related to reconstruction from the window and adds them to dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        conf_map : dict
            contains parameters read from window
        """
        conf_map = {}
        if len(self.reconstructions.text()) > 0:
            conf_map['reconstructions'] = str(self.reconstructions.text())
        if len(self.device.text()) > 0:
            conf_map['device'] = str(self.device.text()).replace('\n','')
        if len(self.alg_seq.text()) > 0:
            conf_map['algorithm_sequence'] = str(self.alg_seq.text()).replace('\n','')
        if len(self.beta.text()) > 0:
            conf_map['beta'] = str(self.beta.text())
        if self.cont.isChecked():
            conf_map['continue_dir'] = str(self.cont_dir.text())

        for feat_id in self.features.feature_dir:
            self.features.feature_dir[feat_id].add_config(conf_map)

        return conf_map


    def get_disp_config(self):
        """
        It reads parameters related to visualization from the window and adds them to dictionary.

        Parameters
        ----------
        none

        Returns
        -------
        conf_map : dict
            contains parameters read from window
        """
        conf_map = {}
        if self.results_dir is not None:
            conf_map['results_dir'] = '"' + str(self.results_dir).strip() + '"'
        if len(self.energy.text()) > 0:
            conf_map['energy'] = str(self.energy.text())
        if len(self.delta.text()) > 0:
            conf_map['delta'] = str(self.delta.text())
        if len(self.gamma.text()) > 0:
            conf_map['gamma'] = str(self.gamma.text())
        if len(self.detdist.text()) > 0:
            conf_map['detdist'] = str(self.detdist.text())
        if len(self.theta.text()) > 0:
            conf_map['theta'] = str(self.theta.text())
        if len(self.chi.text()) > 0:
            conf_map['chi'] = str(self.chi.text())
        if len(self.phi.text()) > 0:
            conf_map['phi'] = str(self.phi.text())
        if len(self.scanmot.text()) > 0:
            conf_map['scanmot'] = '"' + str(self.scanmot.text()) + '"'
        if len(self.scanmot_del.text()) > 0:
            conf_map['scanmot_del'] = str(self.scanmot_del.text())
        if len(self.detector.text()) > 0:
            conf_map['detector'] = '"' + str(self.detector.text()) + '"'
        if len(self.diffractometer.text()) > 0:
            conf_map['diffractometer'] = '"' + str(self.diffractometer.text()) + '"'
        if len(self.crop.text()) > 0:
            conf_map['crop'] = str(self.crop.text()).replace('\n', '')
        if len(self.rampups.text()) > 0:
            conf_map['rampups'] = str(self.rampups.text()).replace('\n', '')

        return conf_map


    def load_prep_conf(self):
        """
        TODO: combine all load conf files in one function
        It display a select dialog for user to select a configuration file for preparation. When selected, the parameters from that file will be loaded to the window.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        prep_file = select_file(os.getcwd())
        if prep_file is not None:
            self.load_prep_tab(prep_file)
            self.set_prep_conf_from_button.setStyleSheet("Text-align:left")
            self.set_prep_conf_from_button.setText('config loaded')
            self.set_prep_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
        else:
            msg_window('please select valid prep config file')


    def load_data_conf(self):
        """
        It display a select dialog for user to select a configuration file. When selected, the parameters from that file will be loaded to the window.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        data_file = select_file(os.getcwd())
        if data_file is not None:
            self.load_data_tab(data_file)
            self.set_data_conf_from_button.setStyleSheet("Text-align:left")
            self.set_data_conf_from_button.setText('config loaded')
            self.set_data_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
            # # save data config
            # conf_map = self.get_data_config()
            # self.main_win.write_conf(conf_map, os.path.join(self.main_win.experiment_dir, 'conf'), 'config_data')
        else:
            msg_window('please select valid data config file')

    def load_rec_conf_dir(self):
        """
        It display a select dialog for user to select a configuration file. When selected, the parameters from that file will be loaded to the window.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        rec_file = select_file(os.getcwd())
        if rec_file is not None:
            self.load_rec_tab(rec_file)
            self.set_rec_conf_from_button.setStyleSheet("Text-align:left")
            self.set_rec_conf_from_button.setText('config loaded')
            self.set_rec_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
            # # save rec config
            # conf_map = self.get_rec_config()
            # self.main_win.write_conf(conf_map, os.path.join(self.main_win.experiment_dir, 'conf'), 'config_rec')
        else:
            msg_window('please select valid rec config file')


    def load_disp_conf(self):
        """
        It display a select dialog for user to select a configuration file. When selected, the parameters from that file will be loaded to the window.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        disp_file = select_file(os.getcwd())
        if disp_file is not None:
            self.load_disp_tab(disp_file)
            self.set_disp_conf_from_button.setStyleSheet("Text-align:left")
            self.set_disp_conf_from_button.setText('config loaded')
            self.set_disp_conf_from_button.setStyleSheet("background-color:rgb(205,178,102)")
            self.parse_spec()
            # # save disp config
            # conf_map = self.get_disp_config()
            # self.main_win.write_conf(conf_map, os.path.join(self.main_win.experiment_dir, 'conf'), 'config_disp')
        else:
            msg_window('please select valid disp config file')


    def set_overriden(self, item):
        """
        Helper function that will set the text color to black.

        Parameters
        ----------
        item : widget

        Returns
        -------
        nothing
        """
        item.setStyleSheet('color: black')


    def parse_spec(self):
        """
        Calls utility function to parse spec file. Displas the parsed parameters in the window with blue text.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        import reccdi.src_py.beamlines.aps_34id.spec as spec

        if not self.main_win.is_exp_exists():
            # do not parse on initial assignment
            return
        try:
            last_scan = int(self.main_win.scan.split('-')[-1])
            detector_name, roi = spec.get_det_from_spec(self.main_win.specfile, last_scan)
            self.roi.setText(str(roi))
            self.roi.setStyleSheet('color: blue')
            delta, gamma, theta, phi, chi, scanmot, scanmot_del, detdist, detector_name, energy = spec.parse_spec(self.main_win.specfile, last_scan)
            if energy is not None:
                self.energy.setText(str(energy))
                self.energy.setStyleSheet('color: blue')
            if delta is not None:
                self.delta.setText(str(delta))
                self.delta.setStyleSheet('color: blue')
            if gamma is not None:
                self.gamma.setText(str(gamma))
                self.gamma.setStyleSheet('color: blue')
            if theta is not None:
                self.theta.setText(str(theta))
                self.theta.setStyleSheet('color: blue')
            if chi is not None:
                self.chi.setText(str(chi))
                self.chi.setStyleSheet('color: blue')
            if phi is not None:
                self.phi.setText(str(phi))
                self.phi.setStyleSheet('color: blue')
            if detdist is not None:
                self.detdist.setText(str(detdist))
                self.detdist.setStyleSheet('color: blue')
            if scanmot is not None:
                self.scanmot.setText(str(scanmot))
                self.scanmot.setStyleSheet('color: blue')
            if scanmot_del is not None:
                self.scanmot_del.setText(str(scanmot_del))
                self.scanmot_del.setStyleSheet('color: blue')
            if detector_name is not None:
                self.detector.setText(str(detector_name))
                self.detector.setStyleSheet('color: blue')
        except Exception as e:
            print(str(e))
            msg_window ('error parsing spec')


    def set_dark_file(self):
        """
        It display a select dialog for user to select a darkfield file.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.darkfield_filename = select_file(self.darkfield_filename)
        if self.darkfield_filename is not None:
            self.dark_file_button.setStyleSheet("Text-align:left")
            self.dark_file_button.setText(self.darkfield_filename)
        else:
            self.dark_file_button.setText('')


    def set_white_file(self):
        """
        It display a select dialog for user to select a whitefield file.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.whitefield_filename = select_file(self.whitefield_filename)
        if self.whitefield_filename is not None:
            self.white_file_button.setStyleSheet("Text-align:left")
            self.white_file_button.setText(self.whitefield_filename)
        else:
            self.white_file_button.setText('')


    def set_data_dir(self):
        """
        It display a select dialog for user to select a directory with raw data file.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.data_dir = select_dir(self.data_dir)
        if self.data_dir is not None:
            self.data_dir_button.setStyleSheet("Text-align:left")
            self.data_dir_button.setText(self.data_dir)
        else:
            self.data_dir_button.setText('')


    def set_prep_file(self):
        """
        It display a select dialog for user to select a prepared data file.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.prep_file = select_file(self.main_win.working_dir)
        if self.prep_file is not None:
            selected = str(self.prep_file)
            if not selected.endswith('tif') and not selected.endswith('tiff'):
                msg_window("the file extension must be tif or tiff")
                return
            self.ready_prep.setStyleSheet("Text-align:left")
            self.ready_prep.setText(self.prep_file)
        else:
            self.ready_prep.setText('')


    def set_prep_script(self):
        """
        It display a select dialog for user to select a user provided script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.script = select_file(self.main_win.working_dir)
        if self.script is not None:
            self.script_button.setStyleSheet("Text-align:left")
            self.script_button.setText(self.script)
            # fill the arguments with experiment_dir, scans, config file
            conf_file = os.path.join(self.main_win.experiment_dir, 'conf', 'config_prep')
            self.args.setText(str(self.main_win.experiment_dir) + ',' + str(self.main_win.scan) + ',' + conf_file)
        else:
            self.script_button.setText('')


    def prepare(self):
        """
        There is a choice for the user to obtain prepare data. User can use a script written for the 34-IDC beamline, if applies,or can get the prepared file by copying already prepared file from file system. Another option is to use own script.
        This function determines the choice and calls appropriate function.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        if not self.main_win.is_exp_exists():
            msg_window('the experiment has not been created yet')
        elif not self.main_win.is_exp_set():
            msg_window('the experiment has changed, pres "set experiment" button')
        else:
            conf_map = self.get_prep_config()
            if str(self.prep.currentText()) == "custom":
                self.prepare_custom(conf_map)
            elif str(self.prep.currentText()) == "34ID prep":
                self.prepare_34id(conf_map)
            elif str(self.prep.currentText()) == "copy from":
                self.prepare_copy(conf_map)


    def prepare_custom(self, conf_map):
        """
        Determines custom script, module, and parameters for the script, adds import to the module, and calls the custom script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        # determine script directory and script name
        if self.script is None:
            msg_window("script not defined")
            return
        full_script = str(self.script)
        script_info = full_script.split('/')
        script = script_info[len(script_info)-1]
        script_dir = full_script[0 : -(len(script)+1)]
        script = script[0 : -3]
        func = str(self.prep_exec.text())
        if len(func) == 0:
            msg_window("function not defined")
            return

        current_dir = os.getcwd()
        args = str(self.args.text())
        if len(args) == 0:
            args = []
        else:
            args = args.split(',')
            for i in range(len(args)):
                try:
                    if args[i].find('.') == -1:
                        args[i] = int(args[i])
                    else:
                        args[i] = float(args[i])
                except:
                    pass
                try:
                    if args[i].find('-') > -1:
                        l = args[i].split('-')
                        nl = []
                        for n in l:
                            nl.append(int(n))
                        args[i] = nl
                except:
                    pass

        os.chdir(script_dir)
        sys.path.append(script_dir)
        if not self.imported_script:
            self.m = importlib.import_module(script)
            self.imported_script = True
        else:
            self.m = importlib.reload(self.m)
        os.chdir(current_dir)
        f = getattr(self.m, func)
        conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')
        if self.main_win.write_conf(conf_map, conf_dir, 'config_prep'):
            try:
                prep_data = f(*args)
            except Exception as e:
                msg_window('custom script failed ' + str(e))
                return
            if prep_data is not None:
                tif_file = os.path.join(self.main_win.experiment_dir, 'prep', 'prep_data.tif')
                ut.save_tif(prep_data, tif_file)
                print ('done with prep')


    def prepare_34id(self, conf_map):
        """
        Reads the parameters needed by prep script. Saves the config_prep configuration file with parameters from the window and runs the prep script.
        
        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        import run_prep_34idc as prep

        # for 34idc prep data directory is needed
        if self.data_dir is None:
            msg_window('cannot prepare data for 34idc, need data directory')
            return
        # for 34idc prep specfile or roi is needed
        if self.main_win.specfile == None:
            msg_window('cannot prepare data for 34idc, need specfile')
            return
        # for 34idc prep scan is needed
        scan = str(self.main_win.scan_widget.text())
        if len(scan) == 0:
            msg_window(('cannot prepare data for 34idc, scan not specified'))
            return
        try:
            # after checking that scan is entered convert it to list of int
            scan_range = scan.split('-')
            for i in range(len(scan_range)):
                scan_range[i] = int(scan_range[i])
        except:
            pass

        conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')
        conf_file = os.path.join(conf_dir, 'config_prep')
        if self.main_win.write_conf(conf_map, conf_dir, 'config_prep'):
            #f = getattr(mod, 'main')
            #f(self.main_win.experiment_dir)
            prep.set_prep(self.main_win.experiment_dir)
        if self.separate_scans.isChecked():
            self.results_dir = self.main_win.experiment_dir
        self.result_dir_button.setStyleSheet("Text-align:left")
        self.result_dir_button.setText(self.results_dir)


    def prepare_copy(self, conf_map):
        """
        Reads the parameters needed by prep script. Saves the config_prep configuration file with parameters from the window and runs the prep script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        # save the file as experiment prep file
        prep_dir = os.path.join(self.main_win.experiment_dir, 'prep')
        if not os.path.exists(prep_dir):
            os.makedirs(prep_dir)
        exp_prep_file = os.path.join(prep_dir, 'prep_data.tif')
        shutil.copyfile(self.prep_file, exp_prep_file)
        # save config_prep
        conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')
        self.main_win.write_conf(conf_map, conf_dir, 'config_prep')


    def format_data(self):
        """
        Reads the parameters needed by format data script. Saves the config_data configuration file with parameters from the window and runs the format script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        import format_data as run_dt

        if not self.main_win.is_exp_exists():
            msg_window('the experiment has not been created yet')
        elif not self.main_win.is_exp_set():
            msg_window('the experiment has changed, pres "set experiment" button')
        elif len(self.amp_intensity.text()) == 0:
            msg_window('Please, enter amp intensity parameter')
        else:
            if os.path.isfile(os.path.join(self.main_win.experiment_dir, 'prep','prep_data.tif'))\
                    or self.separate_scans.isChecked():
                conf_map = self.get_data_config()
                conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')
                if self.main_win.write_conf(conf_map, conf_dir, 'config_data'):
                    run_dt.data(self.main_win.experiment_dir)
            else:
                msg_window('Please, run data preparation in previous tab to activate this function')


    def reconstruction(self):
        """
        Reads the parameters needed by reconstruction script. Saves the config_rec configuration file with parameters from the window and runs the reconstruction script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        import run_rec as run_rc

        if not self.main_win.is_exp_exists():
            msg_window('the experiment has not been created yet')
        elif not self.main_win.is_exp_set():
            msg_window('the experiment has changed, pres "set experiment" button')
        else:
            if os.path.isfile(os.path.join(self.main_win.experiment_dir, 'data', 'data.tif'))\
                    or self.separate_scans.isChecked():
                # find out which configuration should be saved
                if self.old_conf_id == '':
                    conf_file = 'config_rec'
                    conf_id = None
                else:
                    conf_file = self.old_conf_id + '_config_rec'
                    conf_id = self.old_conf_id

                conf_map = self.get_rec_config()
                conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')

                if self.main_win.write_conf(conf_map, conf_dir, conf_file):
                    run_rc.manage_reconstruction(str(self.proc.currentText()), self.main_win.experiment_dir, conf_id)

                    # set the results_dir in display tab.
                    self.init_results_dir()
            else:
                msg_window('Please, run format data in previous tab to activate this function')


    def init_results_dir(self):
        """
        Results directory is a parameter in display tab. It defines a directory tree that the display script will search for reconstructed image files and will process them for visualization. This function initializes it in typical situation to experiment directory. In case of active genetic algorithm it will be initialized to the generation directory with best results, and in case of alternate reconstruction configuration, it will be initialized to the last directory where the results were saved.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        # if alternate configuration was chosen in reconstruction tab, use it in results_dir
        if self.old_conf_id == '':
            res_file = 'results'
        else:
            res_file = self.old_conf_id + '_results'
        # set the results_dir in display tab. If GA, set it to the best results dir, if separate scans
        # set to experiment
        ga_feat = self.features.feature_dir['GA']
        if ga_feat.active.isChecked() and int(ga_feat.generations.text()) > 1:
            generations = int(ga_feat.generations.text())
            # if only one reconstruction, it will be saved in gen dir, otherwise,
            # the directories will be enumerated
            if int(self.reconstructions.text()) > 1:
                self.results_dir = os.path.join(self.main_win.experiment_dir, res_file,
                                                'g_' + str(generations-1), '0')
            else:
                self.results_dir = os.path.join(self.main_win.experiment_dir, res_file,
                                                'g_' + str(generations-1))
        else:
            self.results_dir = os.path.join(self.main_win.experiment_dir, res_file)
        if self.separate_scans.isChecked():
            self.results_dir = self.main_win.experiment_dir
        self.result_dir_button.setStyleSheet("Text-align:left")
        self.result_dir_button.setText(self.results_dir)


    def set_results_dir(self):
        """
        Results directory is a parameter in display tab. It defines a directory tree that the display script will search for reconstructed image files and will process them for visualization. This function displays the dialog selection window for the user to select the results directory.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        if self.main_win.is_exp_exists():

            self.results_dir = os.path.join(self.main_win.experiment_dir, 'results')
            self.results_dir = select_dir(self.results_dir)
            if self.results_dir is not None:
                self.result_dir_button.setStyleSheet("Text-align:left")
                self.result_dir_button.setText(self.results_dir)
            else:
                self.result_dir_button.setText('')
        else:
            msg_window('the experiment has not been created yet')


    def display(self):
        """
        Reads the parameters needed by format display script. Saves the config_disp configuration file with parameters from the window and runs the display script.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        import run_disp as run_dp

        if not self.main_win.is_exp_exists():
            msg_window('the experiment has not been created yet')
            return
        if not self.main_win.is_exp_set():
            msg_window('the experiment has changed, pres "set experiment" button')
            return
        if len(self.diffractometer.text()) == 0:
            msg_window('please enter the diffractometer in display tab')
            return
        else:
            # check if the diffractometer is defined
            diffObj = dif.getdiffclass(self.diffractometer.text())
            if diffObj is None:
                msg_window('the diffractometer is not defined')
                return
        # check if the results exist
        if self.results_dir is None:
            self.results_dir = self.main_win.experiment_dir
        is_result = False
        for (dirpath, dirnames, filenames) in os.walk(self.results_dir):
            for file in filenames:
                if file.endswith('image.npy'):
                    is_result = True
                    break
            if is_result:
                break
        if not is_result:
            msg_window('No image files found in the results directory tree. Please, run reconstruction in previous tab to activate this function')
            return
        if (self.main_win.specfile is None or not os.path.isfile(self.main_win.specfile)) and \
           (len(self.energy.text()) == 0 or \
            len(self.delta.text()) == 0 or \
            len(self.gamma.text()) == 0 or \
            len(self.detdist.text()) == 0 or \
            len(self.theta.text()) == 0 or \
            len(self.detector.text()) == 0):
                msg_window('Please, enter valid spec file or all detector parameters')
                return

        conf_map = self.get_disp_config()

        conf_dir = os.path.join(self.main_win.experiment_dir, 'conf')
        if self.main_win.write_conf(conf_map, conf_dir, 'config_disp'):
            run_dp.to_vtk(self.main_win.experiment_dir)


    def rec_default(self):
        """
        Sets the basic parameters in the reconstruction tab main part to hardcoded defaults.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        if  self.main_win.working_dir is None or self.main_win.id is None or \
            len(self.main_win.working_dir) == 0 or len(self.main_win.id) == 0:
            msg_window('Working Directory or Reconstruction ID not configured')
        else:
            self.reconstructions.setText('1')
            self.device.setText('(0,1)')
            self.alg_seq.setText('((3,("ER",20),("HIO",180)),(1,("ER",20)))')
            self.beta.setText('.9')
            self.cont.setChecked(False)


class Feature(object):
    """
    This is a parent class to concrete feature classes.
    """
    def __init__(self):
        """
        Constructor, each feature object contains QWidget.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.stack = QWidget()


    def stackUI(self, item, feats):
        """
        Used by all sub-classes (features) when initialized.

        Parameters
        ----------
        item : item from QListWidget
            item represents a feature
        feats : Features object
            Features object is a composition of features

        Returns
        -------
        nothing
        """
        layout = QFormLayout()
        self.active = QCheckBox("active")
        layout.addWidget(self.active)
        self.toggle(layout, item, feats)
        self.stack.setLayout(layout)
        self.active.stateChanged.connect(lambda: self.toggle(layout, item, feats))


    def toggle(self, layout, item, feats):
        """
        Used by sub-classes (features) when a feature is activated or deactivated.

        Parameters
        ----------
        item : item from QListWidget
            item represents a feature
        feats : Features object
            Features object is a composition of features

        Returns
        -------
        nothing
        """
        if self.active.isChecked():
            self.fill_active(layout)

            self.default_button = QPushButton('set to defaults', feats)
            layout.addWidget(self.default_button)
            self.default_button.clicked.connect(self.rec_default)

            item.setForeground(QColor('black'));
        else:
            for i in reversed(range(1, layout.count())):
                layout.itemAt(i).widget().setParent(None)
            item.setForeground(QColor('grey'));


    def fill_active(self, layout):
        """
        This function is overriden in concrete class. It displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        pass


    def rec_default(self):
        """
        This function is overriden in concrete class. It sets feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        pass


    def add_config(self, conf_map):
        """
        This function calls all of the subclasses to add feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        if self.active.isChecked():
            self.add_feat_conf(conf_map)


    def add_feat_conf(self, conf_map):
        """
        This function is overriden in concrete class. It adds feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        pass


    def init_config(self, conf_map):
        """
        This function is overriden in concrete class. It sets feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        pass


class GA(Feature):
    """
    This class encapsulates GA feature.
    """
    def __init__(self):
        super(GA, self).__init__()
        self.id = 'GA'

    # override setting the active to set it False
    def stackUI(self, item, feats):
        super(GA, self).stackUI(item, feats)


    def init_config(self, conf_map):
        """
        This function sets GA feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            gens = conf_map.generations
            self.active.setChecked(True)
            self.generations.setText(str(gens).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.metrics.setText(str(conf_map.ga_metrics).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.breed_modes.setText(str(conf_map.ga_breed_modes).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.removes.setText(str(conf_map.ga_cullings).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.ga_support_thresholds.setText(str(conf_map.ga_support_thresholds).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.ga_support_sigmas.setText(str(conf_map.ga_support_sigmas).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.lr_sigmas.setText(str(conf_map.ga_low_resolution_sigmas).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.generations = QLineEdit()
        layout.addRow("generations", self.generations)
        self.metrics = QLineEdit()
        layout.addRow("fitness metrics", self.metrics)
        self.breed_modes = QLineEdit()
        layout.addRow("breed modes", self.breed_modes)
        self.removes = QLineEdit()
        layout.addRow("cullings", self.removes)
        self.ga_support_thresholds = QLineEdit()
        layout.addRow("after breed support thresholds", self.ga_support_thresholds)
        self.ga_support_sigmas = QLineEdit()
        layout.addRow("after breed support sigmas", self.ga_support_sigmas)
        self.lr_sigmas = QLineEdit()
        layout.addRow("low resolution sigmas", self.lr_sigmas)


    def rec_default(self):
        """
        This function sets GA feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.generations.setText('5')
        self.metrics.setText('("chi","chi","area","chi","sharpness")')
        self.breed_modes.setText('("sqrt_ab","sqrt_ab","avg_ab","max_ab_pa","sqrt_ab")')
        self.removes.setText('(2,2,1)')
        self.ga_support_thresholds.setText('(.1,.1,.1,.1,.1)')
        self.ga_support_sigmas.setText('(1.0,1.0,1.0,1.0)')
        self.lr_sigmas.setText('(2.0,1.5)')
        self.active.setChecked(True)


    def add_feat_conf(self, conf_map):
        """
        This function adds GA feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['generations'] = str(self.generations.text())
        conf_map['ga_metrics'] = str(self.metrics.text()).replace('\n','')
        conf_map['ga_breed_modes'] = str(self.breed_modes.text()).replace('\n','')
        conf_map['ga_cullings'] = str(self.removes.text()).replace('\n','')
        conf_map['ga_support_thresholds'] = str(self.ga_support_thresholds.text()).replace('\n','')
        conf_map['ga_support_sigmas'] = str(self.ga_support_sigmas.text()).replace('\n','')
        conf_map['ga_low_resolution_sigmas'] = str(self.lr_sigmas.text()).replace('\n','')


class low_resolution(Feature):
    """
    This class encapsulates low resolution feature.
    """
    def __init__(self):
        super(low_resolution, self).__init__()
        self.id = 'low resolution'


    def init_config(self, conf_map):
        """
        This function sets low resolution feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.resolution_trigger
            self.active.setChecked(True)
            self.res_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.sigma_range.setText(str(conf_map.iter_res_sigma_range).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.det_range.setText(str(conf_map.iter_res_det_range).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.res_triggers = QLineEdit()
        layout.addRow("low resolution triggers", self.res_triggers)
        self.sigma_range = QLineEdit()
        layout.addRow("sigma range", self.sigma_range)
        self.det_range = QLineEdit()
        layout.addRow("det range", self.det_range)


    def rec_default(self):
        """
        This function sets low resolution feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.res_triggers.setText('(0, 1, 320)')
        self.sigma_range.setText('(2.0)')
        self.det_range.setText('(.7)')


    def add_feat_conf(self, conf_map):
        """
        This function adds low resolution feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['resolution_trigger'] = str(self.res_triggers.text()).replace('\n','')
        conf_map['iter_res_sigma_range'] = str(self.sigma_range.text()).replace('\n','')
        conf_map['iter_res_det_range'] = str(self.det_range.text()).replace('\n','')


class shrink_wrap(Feature):
    """
    This class encapsulates support feature.
    """
    def __init__(self):
        super(shrink_wrap, self).__init__()
        self.id = 'shrink wrap'


    def init_config(self, conf_map):
        """
        This function sets support feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.shrink_wrap_trigger
            self.active.setChecked(True)
            self.shrink_wrap_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.shrink_wrap_type.setText(str(conf_map.shrink_wrap_type).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.support_area.setText(str(conf_map.support_area).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.threshold.setText(str(conf_map.support_threshold).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.sigma.setText(str(conf_map.support_sigma).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.shrink_wrap_triggers = QLineEdit()
        layout.addRow("shrink wrap triggers", self.shrink_wrap_triggers)
        self.shrink_wrap_type = QLineEdit()
        layout.addRow("shrink wrap algorithm", self.shrink_wrap_type)
        self.support_area = QLineEdit()
        layout.addRow("starting support area", self.support_area)
        self.threshold = QLineEdit()
        layout.addRow("threshold", self.threshold)
        self.sigma = QLineEdit()
        layout.addRow("sigma", self.sigma)


    def rec_default(self):
        """
        This function sets support feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.shrink_wrap_triggers.setText('(1,1)')
        self.shrink_wrap_type.setText('GAUSS')
        self.support_area.setText('(.5,.5,.5)')
        self.sigma.setText('1.0')
        self.threshold.setText('0.1')


    def add_feat_conf(self, conf_map):
        """
        This function adds support feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['shrink_wrap_trigger'] = str(self.shrink_wrap_triggers.text()).replace('\n','')
        conf_map['shrink_wrap_type'] = '"' + str(self.shrink_wrap_type.text()) + '"'
        conf_map['support_threshold'] = str(self.threshold.text())
        conf_map['support_sigma'] = str(self.sigma.text())
        conf_map['support_area'] = str(self.support_area.text()).replace('\n','')


class phase_support(Feature):
    """
    This class encapsulates phase support feature.
    """
    def __init__(self):
        super(phase_support, self).__init__()
        self.id = 'phase support'


    def init_config(self, conf_map):
        """
        This function sets phase support feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.phase_support_trigger
            self.active.setChecked(True)
            self.phase_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.phase_min.setText(str(conf_map.phase_min).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.phase_max.setText(str(conf_map.phase_max).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.phase_triggers = QLineEdit()
        layout.addRow("phase support triggers", self.phase_triggers)
        self.phase_min = QLineEdit()
        layout.addRow("phase minimum", self.phase_min)
        self.phase_max = QLineEdit()
        layout.addRow("phase maximum", self.phase_max)


    def rec_default(self):
        """
        This function sets phase support feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.phase_triggers.setText('(0,1,320)')
        self.phase_min.setText('-1.57')
        self.phase_max.setText('1.57')


    def add_feat_conf(self, conf_map):
        """
        This function adds phase support feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['phase_support_trigger'] = str(self.phase_triggers.text()).replace('\n','')
        conf_map['phase_min'] = str(self.phase_min.text())
        conf_map['phase_max'] = str(self.phase_max.text())


class pcdi(Feature):
    """
    This class encapsulates pcdi feature.
    """
    def __init__(self):
        super(pcdi, self).__init__()
        self.id = 'pcdi'


    def init_config(self, conf_map):
        """
        This function sets pcdi feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.pcdi_trigger
            self.active.setChecked(True)
            self.pcdi_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.pcdi_type.setText(str(conf_map.partial_coherence_type).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.pcdi_iter.setText(str(conf_map.partial_coherence_iteration_num).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.pcdi_normalize.setText(str(conf_map.partial_coherence_normalize).replace(" ", ""))
        except AttributeError:
            pass
        try:
            self.pcdi_roi.setText(str(conf_map.partial_coherence_roi).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.pcdi_triggers = QLineEdit()
        layout.addRow("pcdi triggers", self.pcdi_triggers)
        self.pcdi_type = QLineEdit()
        layout.addRow("partial coherence algorithm", self.pcdi_type)
        self.pcdi_iter = QLineEdit()
        layout.addRow("pcdi iteration number", self.pcdi_iter)
        self.pcdi_normalize = QLineEdit()
        layout.addRow("normalize", self.pcdi_normalize)
        self.pcdi_roi = QLineEdit()
        layout.addRow("pcdi kernel area", self.pcdi_roi)


    def rec_default(self):
        """
        This function sets pcdi feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.pcdi_triggers.setText('(50,50)')
        self.pcdi_type.setText('LUCY')
        self.pcdi_iter.setText('20')
        self.pcdi_normalize.setText('true')
        self.pcdi_roi.setText('(8,8,8)')


    def add_feat_conf(self, conf_map):
        """
        This function adds pcdi feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['pcdi_trigger'] = str(self.pcdi_triggers.text()).replace('\n','')
        conf_map['partial_coherence_type'] = '"' + str(self.pcdi_type.text()) + '"'
        conf_map['partial_coherence_iteration_num'] = str(self.pcdi_iter.text())
        conf_map['partial_coherence_normalize'] = str(self.pcdi_normalize.text())
        conf_map['partial_coherence_roi'] = str(self.pcdi_roi.text()).replace('\n','')


class twin(Feature):
    """
    This class encapsulates twin feature.
    """
    def __init__(self):
        super(twin, self).__init__()
        self.id = 'twin'


    def init_config(self, conf_map):
        """
        This function sets twin feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.twin_trigger
            self.active.setChecked(True)
            self.twin_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return
        try:
            self.twin_halves.setText(str(conf_map.twin_halves).replace(" ", ""))
        except AttributeError:
            pass


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.twin_triggers = QLineEdit()
        layout.addRow("twin triggers", self.twin_triggers)
        self.twin_halves = QLineEdit()
        layout.addRow("twin halves", self.twin_halves)


    def rec_default(self):
        """
        This function sets twin feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.twin_triggers.setText('(2)')
        self.twin_halves.setText('(0,0)')


    def add_feat_conf(self, conf_map):
        """
        This function adds twin feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['twin_trigger'] = str(self.twin_triggers.text()).replace('\n','')
        conf_map['twin_halves'] = str(self.twin_halves.text()).replace('\n','')


class average(Feature):
    """
    This class encapsulates average feature.
    """
    def __init__(self):
        super(average, self).__init__()
        self.id = 'average'


    def init_config(self, conf_map):
        """
        This function sets average feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.average_trigger
            self.active.setChecked(True)
            self.average_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.average_triggers = QLineEdit()
        layout.addRow("average triggers", self.average_triggers)


    def rec_default(self):
        """
        This function sets average feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.average_triggers.setText('(-50,1)')


    def add_feat_conf(self, conf_map):
        """
        This function adds average feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['average_trigger'] = str(self.average_triggers.text()).replace('\n','')


class progress(Feature):
    """
    This class encapsulates progress feature.
    """
    def __init__(self):
        super(progress, self).__init__()
        self.id = 'progress'


    def init_config(self, conf_map):
        """
        This function sets progress feature's parameters to parameters in dictionary and displays in the window.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        try:
            triggers = conf_map.progress_trigger
            self.active.setChecked(True)
            self.progress_triggers.setText(str(triggers).replace(" ", ""))
        except AttributeError:
            self.active.setChecked(False)
            return


    def fill_active(self, layout):
        """
        This function displays the feature's parameters when the feature becomes active.

        Parameters
        ----------
        layout : Layout widget
            a layout with the feature

        Returns
        -------
        nothing
        """
        self.progress_triggers = QLineEdit()
        layout.addRow("progress triggers", self.progress_triggers)


    def rec_default(self):
        """
        This function sets progress feature's parameters to hardcoded default values.

        Parameters
        ----------
        none

        Returns
        -------
        nothing
        """
        self.progress_triggers.setText('(0,20)')


    def add_feat_conf(self, conf_map):
        """
        This function adds progress feature's parameters to dictionary.

        Parameters
        ----------
        conf_map : dict
            contains parameters for reconstruction

        Returns
        -------
        nothing
        """
        conf_map['progress_trigger'] = str(self.progress_triggers.text()).replace('\n','')



class Features(QWidget):
    """
    This class is composition of all feature classes.
    """
    def __init__(self, tab, layout):
        """
        Constructor, creates all concrete feature objects, and displays in window.
        """
        super(Features, self).__init__()
        feature_ids = ['GA', 'low resolution', 'shrink wrap', 'phase support', 'pcdi', 'twin', 'average', 'progress']
        self.leftlist = QListWidget()
        self.feature_dir = {'GA' : GA(),
                            'low resolution' : low_resolution(),
                            'shrink wrap' : shrink_wrap(),
                            'phase support' : phase_support(),
                            'pcdi' : pcdi(),
                            'twin' : twin(),
                            'average' : average(),
                            'progress' : progress()}
        self.Stack = QStackedWidget(self)
        for i in range(len(feature_ids)):
            id = feature_ids[i]
            self.leftlist.insertItem(i, id)
            feature = self.feature_dir[id]
            feature.stackUI(self.leftlist.item(i), self)
            self.Stack.addWidget(feature.stack)

        layout.addWidget(self.leftlist)
        layout.addWidget(self.Stack)

        self.leftlist.currentRowChanged.connect(self.display)


    def display(self, i):
        self.Stack.setCurrentIndex(i)


def main():
    """
    Starts GUI application.
    """
    app = QApplication(sys.argv)
    ex = cdi_gui()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
