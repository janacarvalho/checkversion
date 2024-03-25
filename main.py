import sys
import os
import re
import shotgun_api3
import sgtk

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


def connect_to_shotgrid():
    url = 'https://your.domain.com/'
    script_name = 'script_name'
    script_key = 'abcdefghijklmnopqrstuvwxyz'

    # Connect to Shotgrid
    sg = shotgun_api3.Shotgun(url, script_name, script_key)
    return sg  # Return the connection object


class ShotgridData:
    def __init__(self):
        self.non_standard_versions = []

    def get_projects(self):
        sg = connect_to_shotgrid()
        project_lst = sg.find("Project",
                              filters=[],
                              fields=["type", "id", "name"])
        projects_name = [project["name"] for project in project_lst]
        projects_name = sorted(projects_name, key=lambda s: s.lower())
        return projects_name

    def get_project_name(self, id):
        sg = connect_to_shotgrid()
        project = sg.find_one("Project",
                              filters=[["id", "is", id]],
                              fields=["type", "id", "name"])
        return project["name"]

    def get_project_id(self, project_name):
        sg = connect_to_shotgrid()
        project = sg.find_one("Project",
                              filters=[["name", "is", project_name]],
                              fields=["type", "id", "name"])
        return project["id"]

    def get_sequences(self, project_id):
        sg = connect_to_shotgrid()
        sequence_lst = sg.find("Sequence",
                               filters=[["project", "is", {"type": "Project", "id": project_id}]],
                               fields=["type", "id", "code"])
        sequences_name = [sequence["code"] for sequence in sequence_lst]
        return sequences_name

    def get_sequences_from_name(self, project_name):
        project_id = self.get_project_id(project_name)
        return self.get_sequences(project_id)

    def get_shots(self, project_name, sequence_name):
        sg = connect_to_shotgrid()
        project_id = self.get_project_id(project_name)
        filters = [["project", "is", {"type": "Project", "id": project_id}], ["code", "is", sequence_name]]
        fields = ["shots"]
        shots_info = sg.find_one("Sequence", filters, fields)
        return [shot["name"] for shot in shots_info["shots"]]

    def get_shot_id(self, project, shot):
        sg = connect_to_shotgrid()
        project_id = self.get_project_id(project)
        shot_filters = [["project", "is", {"type": "Project", "id": project_id}], ["code", "is", shot]]
        shot_fields = ["type", "id", "code"]
        shot_info = sg.find_one("Shot", shot_filters, shot_fields)
        return shot_info["id"]

    def validate_version(self, version):
        version_pattern = r"^(?P<sequence>[^_]*)_(?P<shot>\w*).(?P<task>\w*).(?P<version>v\d{3})$"
        match = re.search(version_pattern, version["version_name"])
        if (match.group("sequence") == version["sequence"] and
                match.group("shot") == version["shot_name"] and
                match.group("task") == version["task"].lower() and
                match.group("version")):
            return ""
        else:
            suggested_name = "{sequence}_{shot}.{pipeline_step}.{version}".format(
                sequence=version["sequence"],
                shot=version["shot_name"],
                pipeline_step=version["task"].lower(),
                version=match.group("version")
            )
            return suggested_name

    def validate_path_to_frames(self, version):
        frames_pttn = r"^(?P<sequence>[^_]*)_(?P<shot>\w*).(?P<task>\w*).(?P<version>v\d{3}).(?P<udim>.*)$"
        directory = os.path.dirname(version["version_path_to_frames"])
        filename, extension = os.path.splitext(os.path.basename(version["version_path_to_frames"]))
        match = re.search(frames_pttn, filename)
        proposed_path_to_frames = ""
        standard = True
        if match:
            standard = match.group("sequence") == version["sequence"] and standard
            standard = match.group("shot") == version["shot_name"] and standard
            standard = match.group("task") == version["task"].lower() and standard
            standard = match.group("version") and standard
            standard = match.group("udim") == "%04d" and standard
            standard = extension == ".exr" and standard
        else:
            standard = False
        if not standard:
            proposed_path_to_frames = "{sequence}_{shot}.{pipeline_step}.{version}.{udim}{ext}".format(
                sequence=version["sequence"],
                shot=version["shot_name"],
                pipeline_step=version["task"].lower(),
                version=match.group("version"),
                udim="%04d",
                ext=".exr"
            )
            proposed_path_to_frames = '/'.join([directory, proposed_path_to_frames])
        return proposed_path_to_frames

    def validate_path_to_movie(self, version):
        movie_pttn = r"^(?P<sequence>[^_]*)_(?P<shot>\w*).(?P<task>\w*).(?P<version>v\d{3})$"
        directory = os.path.dirname(version["version_path_to_movie"])
        filename, extension = os.path.splitext(os.path.basename(version["version_path_to_movie"]))
        match = re.search(movie_pttn, filename)
        proposed_path_to_movie = ""
        standard = True
        if match:
            standard = match.group("sequence") == version["sequence"] and standard
            standard = match.group("shot") == version["shot_name"] and standard
            standard = match.group("task") == version["task"].lower() and standard
            standard = match.group("version") and standard
            standard = extension == ".mov" and standard
        else:
            standard = False
        if not standard:
            proposed_path_to_movie = "{sequence}_{shot}.{pipeline_step}.{version}{ext}".format(
                sequence=version["sequence"],
                shot=version["shot_name"],
                pipeline_step=version["task"].lower(),
                version=match.group("version"),
                ext=".mov"
            )
            proposed_path_to_movie = '/'.join([directory, proposed_path_to_movie])
        return proposed_path_to_movie

    def get_version_data(self, project, sequence, shot):
        sg = connect_to_shotgrid()
        project_id = self.get_project_id(project)
        shot_id = self.get_shot_id(project, shot)
        version_filter = [['project', 'is', {'type': 'Project', 'id': project_id}],
                          ['entity', 'is', {'type': 'Shot', 'id': shot_id}]]
        version_fields = ['entity', 'sg_path_to_frames', 'sg_path_to_movie', 'sg_task', 'code']
        versions = sg.find("Version", version_filter, version_fields)

        for version in versions:
            version_name = version["code"]
            shot_name = version["entity"]["name"]
            version_id = version["id"]
            version_path_to_frames = version["sg_path_to_frames"]
            version_path_to_movie = version["sg_path_to_movie"]
            task = version["sg_task"]["name"]
            version_item = {"version_name": version_name,
                            "sequence": sequence,
                            "shot_name": shot_name,
                            "version_id": version_id,
                            "version_path_to_frames": version_path_to_frames,
                            "version_path_to_movie": version_path_to_movie,
                            "task": task,
                            "proposed_version_name": "",
                            "proposed_path_to_frames": "",
                            "proposed_path_to_movie": "",
                            "non_standard": True}
            version_item["proposed_version_name"] = self.validate_version(version_item)
            version_item["proposed_path_to_frames"] = self.validate_path_to_frames(version_item)
            version_item["proposed_path_to_movie"] = self.validate_path_to_movie(version_item)

            version_item["non_standard"] = bool(version_item["proposed_version_name"] or
                                                version_item["proposed_path_to_frames"] or
                                                version_item["proposed_path_to_movie"])
            self.non_standard_versions.append(version_item)

    def get_formatted_data(self):
        formatted_data = [(version["version_id"],
                          version["version_name"],
                          version["proposed_version_name"],
                          version["version_path_to_frames"],
                          version["proposed_path_to_frames"],
                          version["version_path_to_movie"],
                          version["proposed_path_to_movie"]) for version in self.non_standard_versions
                          if version["non_standard"]]
        return formatted_data

class GUICheckPaths(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Shotgrid - Check Version Paths")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.lbl_project = QLabel("Project:")
        self.lbl_project.setFixedWidth(80)
        self.cbo_project = QComboBox()
        self.cbo_project.setFixedWidth(400)
        self.lbl_sequence = QLabel("Sequence:")
        self.lbl_sequence.setFixedWidth(80)
        self.cbo_sequence = QComboBox()
        self.cbo_sequence.setFixedWidth(150)
        self.lbl_shot = QLabel("Shot:")
        self.lbl_shot.setFixedWidth(80)
        self.cbo_shot = QComboBox()
        self.cbo_shot.setFixedWidth(150)

        self.btn_checkPaths = QPushButton("Check Version Path")
        self.btn_checkPaths.setFixedWidth(200)
        self.btn_checkPaths.clicked.connect(self.check_paths)

        self.tbl_versions = QTableWidget()
        self.tbl_versions.setColumnCount(7)
        self.tbl_versions.setHorizontalHeaderLabels(["ID",
                                                     "Current Version Name",
                                                     "Proposed Version Name",
                                                     "Current Path to Frames",
                                                     "Proposed Path to Frames",
                                                     "Current Path to Movies",
                                                     "Proposed Path to Movie"])
        self.tbl_versions.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        lyt_main = QVBoxLayout()
        self.lyt_filter = QHBoxLayout()
        self.lyt_filter.setContentsMargins(10, 10, 10, 10)
        self.lyt_filter.setAlignment(Qt.AlignLeft)
        self.lyt_filter.setSpacing(10)

        # self.lyt_run_check = QHBoxLayout()

        self.lyt_filter.addWidget(self.lbl_project)
        self.lyt_filter.addWidget(self.cbo_project)
        self.lyt_filter.addWidget(self.lbl_sequence)
        self.lyt_filter.addWidget(self.cbo_sequence)
        self.lyt_filter.addWidget(self.lbl_shot)
        self.lyt_filter.addWidget(self.cbo_shot)
        self.lyt_filter.addWidget(self.btn_checkPaths)

        lyt_main.addLayout(self.lyt_filter)
        lyt_main.addWidget(self.tbl_versions)

        self.central_widget.setLayout(lyt_main)

        self.shotgrid_data = ShotgridData()
        self.load_projects()
        # Set the default project used in the test
        self.cbo_project.setCurrentText(self.shotgrid_data.get_project_name(617))
        self.load_sequences()
        # Set the default sequence used in the test
        self.cbo_sequence.setCurrentText("S01")
        self.load_shots()
        # Set the default shot used in the test
        self.cbo_shot.setCurrentText("AAA_010")
        self.cbo_project.currentIndexChanged.connect(self.load_sequences)
        self.cbo_sequence.currentIndexChanged.connect(self.load_shots)

    def load_projects(self):
        # Load projects available in Shotgrid
        projects = self.shotgrid_data.get_projects()
        self.cbo_project.addItems(projects)

    def load_sequences(self):
        self.cbo_sequence.clear()
        project_name = self.cbo_project.currentText()
        # Load sequence list for the select project from Shotgrid
        sequences = self.shotgrid_data.get_sequences_from_name(project_name)
        self.cbo_sequence.addItems(sequences)
        # self.load_shots()

    def load_shots(self):
        self.cbo_shot.clear()
        project_name = self.cbo_project.currentText()
        sequence_name = self.cbo_sequence.currentText()
        shots = self.shotgrid_data.get_shots(project_name, sequence_name)
        self.cbo_shot.addItems(shots)

    def check_paths(self):
        # Simulated method to fetch data based on selection and populate the table
        project = self.cbo_project.currentText()
        sequence = self.cbo_sequence.currentText()
        shot = self.cbo_shot.currentText()
        self.shotgrid_data.get_version_data(project, sequence, shot)
        self.populate_table(self.shotgrid_data.get_formatted_data())

    def populate_table(self, data):
        self.tbl_versions.setRowCount(0)
        for row_number, row_data in enumerate(data):
            self.tbl_versions.insertRow(row_number)
            for column_number, cell_data in enumerate(row_data):
                self.tbl_versions.setItem(row_number, column_number, QTableWidgetItem(str(cell_data)))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GUICheckPaths()
    window.show()
    sys.exit(app.exec_())
