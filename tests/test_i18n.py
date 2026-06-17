import unittest

from writeonside_app.config import AppConfig, load_config
from writeonside_app.i18n import command_label, get_language, normalize_language, set_language, t


class I18nTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("en")

    def test_normalize_language(self) -> None:
        self.assertEqual("zh", normalize_language("zh-CN"))
        self.assertEqual("pt", normalize_language("pt-BR"))
        self.assertEqual("de", normalize_language("de-DE"))
        self.assertEqual("fr", normalize_language("fr"))
        self.assertEqual("uk", normalize_language("uk-UA"))
        self.assertEqual("en", normalize_language("xx"))

    def test_translations_available(self) -> None:
        set_language("zh")
        self.assertEqual("设置", t("settings.title"))
        set_language("pt")
        self.assertEqual("Definições", t("settings.title"))
        set_language("de")
        self.assertEqual("Einstellungen", t("settings.title"))
        set_language("ko")
        self.assertEqual("설정", t("settings.title"))

    def test_command_label(self) -> None:
        set_language("zh")
        self.assertEqual("新建笔记", command_label("new_note"))

    def test_supported_language_catalogs(self) -> None:
        from writeonside_app.locales import TRANSLATIONS

        for code in ("de", "fr", "nl", "ko", "it", "hi", "uk"):
            set_language(code)
            self.assertEqual(t("settings.title"), TRANSLATIONS[code]["settings.title"])

    def test_config_language_default_and_persist(self) -> None:
        config = AppConfig()
        self.assertEqual("en", config.language)
        set_language(config.language)
        self.assertEqual("en", get_language())


if __name__ == "__main__":
    unittest.main()
