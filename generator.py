import base64
import sys
from typing import List, Dict
from collections import namedtuple
from json import loads as j_loads, dumps as j_dumps

import yaml
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QScrollArea,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

ConfEnt = namedtuple("ConfEnt", ["id", "desc", "default"])


MENIFEST_PATH = "menifest.yaml"


class Configs:
    def __init__(self, title: str, version: str):
        self.title = title
        self.version = version
        self.configs: List[ConfEnt] = []
        self.contents: Dict[str, str] = {}

    def append(self, conf_id: str, desc: str, default: str):
        self.configs.append(ConfEnt(conf_id, desc, default))

    def export_as_json(self) -> str:
        o = j_dumps(self.contents)
        print("Exported json config:", o)
        encoded = base64.b64encode(o.encode("utf-8")).decode("utf-8")
        return encoded

    def load_from_json(self, content: str):
        o = base64.b64decode(content).decode("utf-8")
        print("Loaded json config:", o)
        data = j_loads(o)
        self.contents.clear()
        for k, v in data.items():
            self.contents[k] = v


def parse(configs: Configs, prefix: List[str], o: dict):
    if "ident" in o:
        prefix = prefix + [o["ident"]]
    if "description" in o:
        configs.append(".".join(prefix), o["description"], o["default"])
    for sub in o.get("subs", []):
        parse(configs, prefix, sub)


class SeparatorWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class ConfigEntryWidget(QWidget):
    def __init__(self, conf: ConfEnt, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        row1 = QHBoxLayout()
        desc_label = QLabel(conf.desc)
        id_label = QLabel(conf.id)
        id_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        row1.addWidget(desc_label)
        row1.addWidget(id_label)
        layout.addLayout(row1)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(str(conf.default))
        layout.addWidget(self.line_edit)
        self.setLayout(layout)


class MainWindow(QWidget):
    def __init__(self, configs: Configs):
        self.configs = configs

        super().__init__()
        self.setWindowTitle(f"{configs.title} v{configs.version}")
        self.setMinimumSize(600, 800)

        self.main_layout = QVBoxLayout()

        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存配置")
        self.load_button = QPushButton("加载配置")
        self.export_button = QPushButton("导出配置")
        self.preview_button = QPushButton("预览配置")
        for btn in [
            self.save_button,
            self.load_button,
            self.export_button,
            self.preview_button,
        ]:
            self.button_layout.addWidget(btn)
        self.main_layout.addLayout(self.button_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.addWidget(SeparatorWidget(self))
        self.entry_widgets = []
        for conf in configs.configs:
            entry_widget = ConfigEntryWidget(conf)
            entry_widget.line_edit.textEdited.connect(
                self.mk_on_conf_edited(conf.id, entry_widget.line_edit)
            )
            self.layout.addWidget(entry_widget)
            self.layout.addWidget(SeparatorWidget(self))
            self.entry_widgets.append(entry_widget)
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.save_button.clicked.connect(self.on_save_config)
        self.load_button.clicked.connect(self.on_load_config)

        self.setLayout(self.main_layout)

    def mk_on_conf_edited(self, key: str, lineedit: QLineEdit):
        def inner():
            text = lineedit.text()
            if text:
                self.configs.contents[key] = text
            else:
                del self.configs.contents[key]

        return inner

    def on_save_config(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择保存配置的文件", "", "All Files (*)"
        )
        if file_path:
            try:
                jstr = self.configs.export_as_json()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(jstr)
                QMessageBox.information(self, "保存成功", f"配置已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存配置时出错:\n{e}")

    def on_load_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要加载的配置文件", "", "All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    jstr = f.read()
                self.configs.load_from_json(jstr)
                # 更新界面
                for conf, entry_widget in zip(self.configs.configs, self.entry_widgets):
                    value = str(self.configs.contents.get(conf.id, conf.default))
                    if value == conf.default:
                        entry_widget.line_edit.setText("")
                    else:
                        entry_widget.line_edit.setText(value)
                QMessageBox.information(self, "加载成功", f"配置已从: {file_path} 加载")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载配置时出错:\n{e}")


def launch_gui(configs: Configs):
    app = QApplication(sys.argv)
    window = MainWindow(configs)
    window.show()
    return app.exec()


if __name__ == "__main__":
    menifest = yaml.load(open(MENIFEST_PATH, "r"), yaml.SafeLoader)
    configs = Configs(menifest["meta"]["title"], menifest["meta"]["version"])
    print(f"Welcome to {configs.title} Ver {configs.version}.")

    print("Parsing all the config items ...")
    parse(configs, list(), menifest["config"])
    print(f"We got {len(configs.configs)} config entries in all.")

    r = launch_gui(configs)

    print("Exit with return value:", r)
