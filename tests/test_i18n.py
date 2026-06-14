import unittest

from writeonside_app.config import AppConfig, load_config
from writeonside_app.i18n import command_label, get_language, normalize_language, set_language, t


class I18nTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("en")

    def test_normalize_language(self) -> None:
        self.assertEqual("zh", normalize_language("zh-CN"))
        self.assertEqual("pt", normalize_language("pt-BR"))
        self.assertEqual("en", normalize_language("fr"))

    def test_translations_available(self) -> None:
        set_language("zh")
        self.assertEqual("设置", t("settings.title"))
        set_language("pt")
        self.assertEqual("Definições", t("settings.title"))

    def test_command_label(self) -> None:
        set_language("zh")
        self.assertEqual("新建笔记", command_label("new_note"))

    def test_config_language_default_and_persist(self) -> None:
        config = AppConfig()
        self.assertEqual("en", config.language)
        set_language(config.language)
        self.assertEqual("en", get_language())


if __name__ == "__main__":
    unittest.main()
