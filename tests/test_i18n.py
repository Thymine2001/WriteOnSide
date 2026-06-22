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

    def test_new_folder_messages_exist_in_every_language(self) -> None:
        from writeonside_app.locales import TRANSLATIONS

        required = {
            "cmd.open_file",
            "explorer.menu.new_folder",
            "status.folder_created",
            "error.attachment_cleanup_failed",
            "error.invalid_folder_name",
            "error.folder_exists",
            "error.create_folder_failed",
            "dialog.new_folder_title",
            "dialog.new_folder_prompt",
            "dialog.open_file",
            "dialog.text_and_code_files",
            "dialog.all_files",
            "error.file_not_found",
            "error.open_file_limit",
            "tooltip.find_case_sensitive",
            "find.replace",
            "find.replace_all",
            "editor.read_limited",
            "color.red",
            "color.orange",
            "color.yellow",
            "color.green",
            "color.blue",
            "color.cyan",
            "color.purple",
            "color.black",
        }
        for code, catalog in TRANSLATIONS.items():
            self.assertFalse(required - catalog.keys(), code)

    def test_config_language_default_and_persist(self) -> None:
        config = AppConfig()
        self.assertEqual("en", config.language)
        set_language(config.language)
        self.assertEqual("en", get_language())


if __name__ == "__main__":
    unittest.main()
