"""
Internationalization (i18n) Engine for Zephyrium
Supports 10 major world languages:
- English (en)
- Русский (ru)
- 简体中文 (zh)
- Español (es)
- Deutsch (de)
- Français (fr)
- 日本語 (ja)
- Português (pt)
- Italiano (it)
- Türkçe (tr)
"""
import locale
from typing import Dict, Any

LANGUAGES = {'en': 'English', 'ru': 'Русский', 'zh': '简体中文', 'es': 'Español', 'de': 'Deutsch', 'fr': 'Français', 'ja': '日本語', 'pt': 'Português', 'it': 'Italiano', 'tr': 'Türkçe'}

TRANSLATIONS: Dict[str, Dict[str, str]] = {'en': {'app_title': 'Zephyrium', 'new_tab': 'New Tab', 'close_tab': 'Close Tab', 'duplicate_tab': 'Duplicate Tab', 'split_view': 'Split Screen', 'suspend_tab': 'Suspend Tab (Free RAM)', 'wake_tab': 'Restore Tab', 'tab_suspended_title': 'TAB SUSPENDED // RAM SAVED', 'tab_suspended_hint': 'Click tab in sidebar or tab bar to restore session.', 'mode_minimal': 'Minimal', 'mode_vim': 'Vim Mode', 'tab_orientation': 'Tab Layout Orientation', 'vertical_tabs': 'Vertical Tabs (Sidebar)', 'horizontal_tabs': 'Horizontal Tabs (Top Bar)', 'switch_to_vertical': 'Switch to Vertical Tabs', 'switch_to_horizontal': 'Switch to Horizontal Tabs', 'exit_vim': 'EXIT VIM', 'vim_hint': "[VIM NORMAL] Press ':' or 'o' for command prompt | '?' for help", 'adblock_blocked': 'Blocked ads: {count}', 'adblock_whitelist': "Whitelist domain '{domain}'", 'adblock_unwhitelist': "Remove '{domain}' from whitelist", 'clean_url': 'Clean Tracking Parameters from URL', 'tor_proxy': 'Tor Proxy (SOCKS5 9050): {status}', 'settings': 'Settings & Configuration', 'general': 'General', 'privacy': 'Privacy & AdBlock', 'import': 'Import Data', 'vault': 'Passwords & Cookies', 'appearance': 'Appearance & Modes', 'ai_assistant': 'AI Assistant', 'network': 'Network & Advanced', 'about': 'About', 'vault_locked_title': 'CREDENTIALS VAULT // PROTECTED', 'vault_locked_desc': 'Viewing and exporting stored passwords and cookies requires superuser (sudo) authorization.', 'sudo_password_label': 'Enter sudo password:', 'unlock_vault': 'Unlock Vault', 'lock_vault': 'Lock Vault', 'wrong_sudo_password': 'Authentication failed. Incorrect password.', 'passwords': 'Passwords', 'cookies': 'Cookies', 'export_csv': 'Export to CSV', 'export_json': 'Export to JSON', 'export_netscape': 'Export Netscape TXT', 'add_credential': 'Add Credential', 'domain': 'Domain / URL', 'username': 'Username', 'password': 'Password', 'actions': 'Actions', 'copy_login': 'Copy Login', 'copy_password': 'Copy Password', 'copied': 'Copied to clipboard!', 'search_cookies': 'Filter cookies by domain or name...', 'save_settings': 'Save Preferences', 'cancel': 'Cancel', 'language': 'Language', 'language_note': 'Select interface display language', 'homepage_url': 'Homepage URL:', 'search_engine': 'Default Search Engine:', 'downloads_dir': 'Downloads Directory:', 'browse': 'BROWSE', 'restore_tabs': 'Restore open tabs upon launch', 'enable_adblock': 'Enable Native Network AdBlock & Tracker Blocker', 'clean_urls_label': 'Auto-strip tracking tags (utm_*, fbclid, gclid) from visited links', 'send_dnt_label': "Send 'Do Not Track' (DNT: 1) header on all requests", 'prevent_webrtc_label': 'Prevent WebRTC IP Address Leaking', 'whitelist_title': 'AdBlock Whitelisted Domains (Bypass Filtering):', 'add_domain_btn': '+ ADD DOMAIN', 'remove_domain_btn': 'REMOVE SELECTED DOMAIN', 'select_browser_import': 'Select Installed Browser to Import From:', 'custom_profile_dir': 'Or Specify Custom Profile Directory:', 'items_to_import': 'Items to Import:', 'bookmarks': 'Bookmarks', 'history': 'History', 'start_import_btn': 'START MIGRATION / IMPORT', 'import_csv_btn': 'IMPORT PASSWORDS FROM CSV...', 'show': 'SHOW', 'copy': 'COPY', 'color_theme': 'Color Theme:', 'theme_dark': 'Minimal Dark', 'theme_light': 'Clean Paper Light', 'primary_accent': 'Primary Accent Color:', 'ui_mode_label': 'UI Layout Mode:', 'font_family_label': 'Monospace Font Family:', 'font_size_label': 'UI Base Font Size (px):', 'sidebar_width_label': 'Vertical Tabs Sidebar Width (px):', 'gemini_key_label': 'Gemini API Key (Live Inference):', 'ai_model_label': 'AI Model Selection:', 'fetch_models_btn': 'FETCH AVAILABLE MODELS', 'ai_persona_label': 'System Instruction / AI Persona:', 'enable_gpu': 'Enable Hardware Acceleration (GPU rasterization & zero-copy)', 'proxy_server_label': 'SOCKS5 / HTTP Proxy Server:', 'about_title': 'About Zephyrium', 'save_apply_btn': 'SAVE AND APPLY', 'adblock_title': 'ADS', 'split_title': 'SPLIT', 'downloads_title': 'DL', 'ai_title': 'AI', 'tabs_vert_short': 'TABS: VERT', 'tabs_horiz_short': 'TABS: HORIZ', 'mode_label': 'MODE', 'keybinds': 'KEYBINDS', 'settings_btn': 'SETTINGS', 'new_tab_btn': '+ NEW TAB', 'profile_btn': 'PROFILE', 'url_placeholder': 'Search DuckDuckGo or enter URL... (or press Ctrl+K)', 'ready': 'READY', 'loading_status': 'LOADING {progress}%...', 'settings_saved_msg': 'Settings saved and applied.', 'internal_page': 'INTERNAL', 'collapse_sidebar': 'Collapse Sidebar (Ctrl+[)', 'expand_sidebar': 'Expand Sidebar (Ctrl+[)', 'split_screen': 'Toggle Split Screen (Ctrl+\\)', 'downloads': 'Toggle Downloads (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Toggle AI Assistant & Notes (Ctrl+B)', 'keybinds_tooltip': 'Open Command Palette & Keybinds (Ctrl+K)', 'settings_tooltip': 'Open Settings & Browser Data Importer (Ctrl+,)', 'vertical_btn': 'VERTICAL', 'ai_chat_tab': 'AI CHAT', 'scratchpad_tab': 'SCRATCHPAD', 'select_container': 'Open in Profile Container...'}, 'ru': {'app_title': 'Zephyrium', 'new_tab': 'Новая вкладка', 'close_tab': 'Закрыть вкладку', 'duplicate_tab': 'Дублировать вкладку', 'split_view': 'Разделить экран', 'suspend_tab': 'Усыпить вкладку (Освободить ОЗУ)', 'wake_tab': 'Восстановить вкладку', 'tab_suspended_title': 'ВКЛАДКА ПРИОСТАНОВЛЕНА // ОЗУ ОСВОБОЖДЕНО', 'tab_suspended_hint': 'Нажмите на вкладку для восстановления сессии.', 'mode_minimal': 'Минималистичный', 'mode_vim': 'Vim Mode (без рамок)', 'tab_orientation': 'Ориентация вкладок', 'vertical_tabs': 'Вертикальные вкладки (боковая панель)', 'horizontal_tabs': 'Горизонтальные вкладки (сверху)', 'switch_to_vertical': 'Переключить на вертикальные вкладки', 'switch_to_horizontal': 'Переключить на горизонтальные вкладки', 'exit_vim': 'ВЫЙТИ ИЗ VIM', 'vim_hint': "[VIM NORMAL] Нажмите ':' или 'o' для команд | '?' для справки", 'adblock_blocked': 'Заблокировано рекламы: {count}', 'adblock_whitelist': "Добавить домен '{domain}' в белый список", 'adblock_unwhitelist': "Удалить '{domain}' из белого списка", 'clean_url': 'Очистить URL от трекинговых меток', 'tor_proxy': 'Tor Прокси (SOCKS5 9050): {status}', 'settings': 'Настройки и конфигурация', 'general': 'Общие', 'privacy': 'Приватность и блокировщик', 'import': 'Импорт данных', 'vault': 'Пароли и куки', 'appearance': 'Внешний вид и режимы', 'ai_assistant': 'AI-ассистент', 'network': 'Сеть и система', 'about': 'О браузере', 'vault_locked_title': 'ХРАНИЛИЩЕ УЧЕТНЫХ ДАННЫХ // ЗАЩИЩЕНО', 'vault_locked_desc': 'Для просмотра и экспорта сохраненных паролей и куки требуется подтверждение прав superuser (sudo).', 'sudo_password_label': 'Введите пароль sudo:', 'unlock_vault': 'Разблокировать хранилище', 'lock_vault': 'Заблокировать', 'wrong_sudo_password': 'Ошибка аутентификации. Неверный пароль sudo.', 'passwords': 'Пароли', 'cookies': 'Куки', 'export_csv': 'Экспорт в CSV', 'export_json': 'Экспорт в JSON', 'export_netscape': 'Экспорт в Netscape TXT', 'add_credential': 'Добавить логин/пароль', 'domain': 'Домен / URL', 'username': 'Логин / Пользователь', 'password': 'Пароль', 'actions': 'Действия', 'copy_login': 'Копировать логин', 'copy_password': 'Копировать пароль', 'copied': 'Скопировано в буфер обмена!', 'search_cookies': 'Поиск куки по домену или имени...', 'save_settings': 'Сохранить настройки', 'cancel': 'Отмена', 'language': 'Язык интерфейса', 'language_note': 'Выберите язык отображения браузера', 'homepage_url': 'Домашняя страница:', 'search_engine': 'Поисковая система по умолчанию:', 'downloads_dir': 'Папка загрузок:', 'browse': 'ОБЗОР', 'restore_tabs': 'Восстанавливать открытые вкладки при запуске', 'enable_adblock': 'Включить встроенный блокировщик рекламы и трекеров', 'clean_urls_label': 'Автоматически удалять трекинговые метки (utm_*, fbclid, gclid)', 'send_dnt_label': "Отправлять заголовок 'Do Not Track' (DNT: 1)", 'prevent_webrtc_label': 'Предотвращать утечку IP-адреса через WebRTC', 'whitelist_title': 'Белый список доменов (отключение фильтрации):', 'add_domain_btn': '+ ДОБАВИТЬ ДОМЕН', 'remove_domain_btn': 'УДАЛИТЬ ВЫБРАННЫЙ ДОМЕН', 'select_browser_import': 'Выберите установленный браузер для импорта:', 'custom_profile_dir': 'Или укажите путь к профилю вручную:', 'items_to_import': 'Данные для импорта:', 'bookmarks': 'Закладки', 'history': 'История', 'start_import_btn': 'НАЧАТЬ МИГРАЦИЮ / ИМПОРТ', 'import_csv_btn': 'ИМПОРТ ПАРОЛЕЙ ИЗ CSV...', 'show': 'ПОКАЗАТЬ', 'copy': 'КОПИРОВАТЬ', 'color_theme': 'Цветовая тема:', 'theme_dark': 'Темная тема (Minimal Dark)', 'theme_light': 'Светлая тема (Clean Paper)', 'primary_accent': 'Основной цвет акцента:', 'ui_mode_label': 'Режим интерфейса:', 'font_family_label': 'Моноширинный шрифт:', 'font_size_label': 'Базовый размер шрифта UI (px):', 'sidebar_width_label': 'Ширина боковой панели вкладок (px):', 'gemini_key_label': 'Ключ Gemini API (живой инференс):', 'ai_model_label': 'Выбор AI-модели:', 'fetch_models_btn': 'ЗАГРУЗИТЬ СПИСОК МОДЕЛЕЙ', 'ai_persona_label': 'Системный промпт / персона AI:', 'enable_gpu': 'Аппаратное ускорение (GPU растеризация и zero-copy)', 'proxy_server_label': 'Прокси-сервер SOCKS5 / HTTP:', 'about_title': 'О программе Zephyrium', 'save_apply_btn': 'СОХРАНИТЬ И ПРИМЕНИТЬ', 'adblock_title': 'РЕКЛАМА', 'split_title': 'РАЗДЕЛЕНИЕ', 'downloads_title': 'ЗАГРУЗКИ', 'ai_title': 'ИИ', 'tabs_vert_short': 'ВКЛАДКИ: ВЕРТ', 'tabs_horiz_short': 'ВКЛАДКИ: ГОРИЗ', 'mode_label': 'РЕЖИМ', 'keybinds': 'КЛАВИШИ', 'settings_btn': 'НАСТРОЙКИ', 'new_tab_btn': '+ ВКЛАДКА', 'profile_btn': 'ПРОФИЛЬ', 'url_placeholder': 'Поиск в DuckDuckGo или ввод URL... (или Ctrl+K)', 'ready': 'ГОТОВО', 'loading_status': 'ЗАГРУЗКА {progress}%...', 'settings_saved_msg': 'Настройки сохранены и применены.', 'internal_page': 'СИСТЕМА', 'collapse_sidebar': 'Свернуть панель (Ctrl+[)', 'expand_sidebar': 'Развернуть панель (Ctrl+[)', 'split_screen': 'Разделить экран (Ctrl+\\)', 'downloads': 'Загрузки (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'AI-ассистент и заметки (Ctrl+B)', 'keybinds_tooltip': 'Палитра команд и горячие клавиши (Ctrl+K)', 'settings_tooltip': 'Настройки и импорт данных (Ctrl+,)', 'vertical_btn': 'ВЕРТИКАЛЬНО', 'ai_chat_tab': 'AI ЧАТ', 'scratchpad_tab': 'ЗАМЕТКИ', 'select_container': 'Открыть в контейнере профиля...'}, 'zh': {'app_title': 'Zephyrium 浏览器', 'new_tab': '新建标签页', 'close_tab': '关闭标签页', 'duplicate_tab': '复制标签页', 'split_view': '分屏浏览', 'suspend_tab': '休眠标签页 (释放内存)', 'wake_tab': '恢复标签页', 'tab_suspended_title': '标签页已休眠 // 内存已释放', 'tab_suspended_hint': '点击标签页即可恢复会话。', 'mode_minimal': '极简模式', 'mode_vim': 'Vim 模式 (无边框)', 'tab_orientation': '标签页布局方向', 'vertical_tabs': '垂直标签页 (侧边栏)', 'horizontal_tabs': '水平标签页 (顶部栏)', 'switch_to_vertical': '切换至垂直标签栏', 'switch_to_horizontal': '切换至水平标签栏', 'exit_vim': '退出 VIM', 'vim_hint': "[VIM 正常模式] 按 ':' 或 'o' 输入命令 | '?' 查看帮助", 'adblock_blocked': '已拦截广告: {count}', 'adblock_whitelist': "将域名 '{domain}' 添加至白名单", 'adblock_unwhitelist': "从白名单中移除 '{domain}'", 'clean_url': '清理链接跟踪参数', 'tor_proxy': 'Tor 代理 (SOCKS5 9050): {status}', 'settings': '设置与配置', 'general': '常规', 'privacy': '隐私与广告拦截', 'import': '导入数据', 'vault': '密码与 Cookie', 'appearance': '外观与模式', 'ai_assistant': 'AI 助手', 'network': '网络与系统', 'about': '关于', 'vault_locked_title': '凭证保险库 // 受保护', 'vault_locked_desc': '查看和导出存储的密码及 Cookie 需要超级用户 (sudo) 授权。', 'sudo_password_label': '输入 sudo 密码:', 'unlock_vault': '解锁保险库', 'lock_vault': '锁定', 'wrong_sudo_password': '身份验证失败。密码错误。', 'passwords': '密码', 'cookies': 'Cookie', 'export_csv': '导出为 CSV', 'export_json': '导出为 JSON', 'export_netscape': '导出为 Netscape TXT', 'add_credential': '添加凭证', 'domain': '域名 / URL', 'username': '用户名', 'password': '密码', 'actions': '操作', 'copy_login': '复制用户名', 'copy_password': '复制密码', 'copied': '已复制到剪贴板！', 'search_cookies': '按域名或名称过滤 Cookie...', 'save_settings': '保存首选项', 'cancel': '取消', 'language': '界面语言', 'language_note': '选择浏览器显示语言', 'homepage_url': '主页网址:', 'search_engine': '默认搜索引擎:', 'downloads_dir': '下载目录:', 'browse': '浏览', 'restore_tabs': '启动时恢复打开的标签页', 'enable_adblock': '启用原生网络广告与跟踪器拦截', 'clean_urls_label': '自动清除访问链接中的跟踪标签 (utm_*, fbclid)', 'send_dnt_label': "在所有请求中发送 'Do Not Track' (DNT: 1) 标头", 'prevent_webrtc_label': '防止 WebRTC IP 地址泄露', 'whitelist_title': '广告拦截白名单域名 (跳过过滤):', 'add_domain_btn': '+ 添加域名', 'remove_domain_btn': '移除选中域名', 'select_browser_import': '选择要导入的已安装浏览器:', 'custom_profile_dir': '或指定自定义配置文件目录:', 'items_to_import': '要导入的项目:', 'bookmarks': '书签', 'history': '历史记录', 'start_import_btn': '开始数据迁移 / 导入', 'import_csv_btn': '从 CSV 导入密码...', 'show': '显示', 'copy': '复制', 'color_theme': '色彩主题:', 'theme_dark': '极简暗色', 'theme_light': '清爽亮色 (Paper)', 'primary_accent': '主强调色:', 'ui_mode_label': '界面模式:', 'font_family_label': '等宽字体族:', 'font_size_label': 'UI 基础字号 (px):', 'sidebar_width_label': '垂直标签侧栏宽度 (px):', 'gemini_key_label': 'Gemini API 密钥 (实时推理):', 'ai_model_label': 'AI 模型选择:', 'fetch_models_btn': '获取可用模型列表', 'ai_persona_label': '系统指令 / AI 人设:', 'enable_gpu': '启用硬件加速 (GPU 光栅化与零拷贝)', 'proxy_server_label': 'SOCKS5 / HTTP 代理服务器:', 'about_title': '关于 Zephyrium', 'save_apply_btn': '保存并应用', 'adblock_title': '广告', 'split_title': '分屏', 'downloads_title': '下载', 'ai_title': 'AI', 'tabs_vert_short': '标签: 垂直', 'tabs_horiz_short': '标签: 水平', 'mode_label': '模式', 'keybinds': '快捷键', 'settings_btn': '设置', 'new_tab_btn': '+ 新建标签', 'profile_btn': '配置文件', 'url_placeholder': '在 DuckDuckGo 搜索或输入网址... (或按 Ctrl+K)', 'ready': '就绪', 'loading_status': '加载中 {progress}%...', 'settings_saved_msg': '设置已保存并应用。', 'internal_page': '内置', 'collapse_sidebar': '折叠侧栏 (Ctrl+[)', 'expand_sidebar': '展开侧栏 (Ctrl+[)', 'split_screen': '切换分屏 (Ctrl+\\)', 'downloads': '下载 (Ctrl+Shift+D)', 'ai_assistant_tooltip': '切换 AI 助手与便签 (Ctrl+B)', 'keybinds_tooltip': '打开命令面板与快捷键 (Ctrl+K)', 'settings_tooltip': '打开设置与数据导入 (Ctrl+,)', 'vertical_btn': '垂直', 'ai_chat_tab': 'AI 对话', 'scratchpad_tab': '便签本', 'select_container': '在配置文件容器中打开...'}, 'es': {'app_title': 'Zephyrium', 'new_tab': 'Nueva pestaña', 'close_tab': 'Cerrar pestaña', 'duplicate_tab': 'Duplicar pestaña', 'split_view': 'Pantalla dividida', 'suspend_tab': 'Suspender pestaña (Liberar RAM)', 'wake_tab': 'Restaurar pestaña', 'tab_suspended_title': 'PESTAÑA SUSPENDIDA // RAM LIBERADA', 'tab_suspended_hint': 'Haga clic en la pestaña para restaurar la sesión.', 'mode_minimal': 'Minimalista', 'mode_vim': 'Modo Vim (sin marcos)', 'tab_orientation': 'Orientación de pestañas', 'vertical_tabs': 'Pestañas verticales (barra lateral)', 'horizontal_tabs': 'Pestañas horizontales (barra superior)', 'switch_to_vertical': 'Cambiar a pestañas verticales', 'switch_to_horizontal': 'Cambiar a pestañas horizontales', 'exit_vim': 'SALIR DE VIM', 'vim_hint': "[VIM NORMAL] Presione ':' u 'o' para comandos | '?' para ayuda", 'adblock_blocked': 'Anuncios bloqueados: {count}', 'adblock_whitelist': "Añadir dominio '{domain}' a la lista blanca", 'adblock_unwhitelist': "Eliminar '{domain}' de la lista blanca", 'clean_url': 'Limpiar parámetros de rastreo de URL', 'tor_proxy': 'Proxy Tor (SOCKS5 9050): {status}', 'settings': 'Ajustes y configuración', 'general': 'General', 'privacy': 'Privacidad y bloqueador', 'import': 'Importar datos', 'vault': 'Contraseñas y cookies', 'appearance': 'Apariencia y modos', 'ai_assistant': 'Asistente de IA', 'network': 'Red y avanzado', 'about': 'Acerca de', 'vault_locked_title': 'BAÚL DE CREDENCIALES // PROTEGIDO', 'vault_locked_desc': 'Ver y exportar contraseñas y cookies requiere autorización superusuario (sudo).', 'sudo_password_label': 'Introduzca la contraseña sudo:', 'unlock_vault': 'Desbloquear baúl', 'lock_vault': 'Bloquear', 'wrong_sudo_password': 'Error de autenticación. Contraseña incorrecta.', 'passwords': 'Contraseñas', 'cookies': 'Cookies', 'export_csv': 'Exportar a CSV', 'export_json': 'Exportar a JSON', 'export_netscape': 'Exportar Netscape TXT', 'add_credential': 'Añadir credencial', 'domain': 'Dominio / URL', 'username': 'Usuario', 'password': 'Contraseña', 'actions': 'Acciones', 'copy_login': 'Copiar usuario', 'copy_password': 'Copiar contraseña', 'copied': '¡Copiado al portapapeles!', 'search_cookies': 'Filtrar cookies por dominio o nombre...', 'save_settings': 'Guardar preferencias', 'cancel': 'Cancelar', 'language': 'Idioma de interfaz', 'language_note': 'Seleccione el idioma de visualización', 'homepage_url': 'URL de página de inicio:', 'search_engine': 'Motor de búsqueda predeterminado:', 'downloads_dir': 'Directorio de descargas:', 'browse': 'EXAMINAR', 'restore_tabs': 'Restaurar pestañas abiertas al iniciar', 'enable_adblock': 'Habilitar bloqueador nativo de anuncios y rastreadores', 'clean_urls_label': 'Eliminar automáticamente etiquetas de rastreo (utm_*, fbclid)', 'send_dnt_label': "Enviar encabezado 'Do Not Track' (DNT: 1)", 'prevent_webrtc_label': 'Prevenir fugas de dirección IP mediante WebRTC', 'whitelist_title': 'Dominios en lista blanca (omitir filtrado):', 'add_domain_btn': '+ AÑADIR DOMINIO', 'remove_domain_btn': 'ELIMINAR DOMINIO SELECCIONADO', 'select_browser_import': 'Seleccione el navegador del cual importar:', 'custom_profile_dir': 'O especifique el directorio de perfil personalizado:', 'items_to_import': 'Elementos a importar:', 'bookmarks': 'Marcadores', 'history': 'Historial', 'start_import_btn': 'INICIAR MIGRACIÓN / IMPORTACIÓN', 'import_csv_btn': 'IMPORTAR CONTRASEÑAS DESDE CSV...', 'show': 'MOSTRAR', 'copy': 'COPIAR', 'color_theme': 'Tema de color:', 'theme_dark': 'Oscuro minimalista', 'theme_light': 'Claro limpio (Paper)', 'primary_accent': 'Color de acento principal:', 'ui_mode_label': 'Modo de interfaz:', 'font_family_label': 'Familia de fuente monoespaciada:', 'font_size_label': 'Tamaño de fuente base (px):', 'sidebar_width_label': 'Ancho de barra lateral de pestañas (px):', 'gemini_key_label': 'Clave API de Gemini (inferencia en vivo):', 'ai_model_label': 'Selección de modelo de IA:', 'fetch_models_btn': 'OBTENER MODELOS DISPONIBLES', 'ai_persona_label': 'Instrucción del sistema / Personalidad de IA:', 'enable_gpu': 'Habilitar aceleración por hardware (GPU)', 'proxy_server_label': 'Servidor proxy SOCKS5 / HTTP:', 'about_title': 'Acerca de Zephyrium', 'save_apply_btn': 'GUARDAR Y APLICAR', 'adblock_title': 'ANUNCIOS', 'split_title': 'DIVIDIR', 'downloads_title': 'DESC', 'ai_title': 'IA', 'tabs_vert_short': 'PEST: VERT', 'tabs_horiz_short': 'PEST: HORIZ', 'mode_label': 'MODO', 'keybinds': 'ATAJOS', 'settings_btn': 'AJUSTES', 'new_tab_btn': '+ PESTAÑA', 'profile_btn': 'PERFIL', 'url_placeholder': 'Buscar en DuckDuckGo o escribir URL... (o Ctrl+K)', 'ready': 'LISTO', 'loading_status': 'CARGANDO {progress}%...', 'settings_saved_msg': 'Ajustes guardados y aplicados.', 'internal_page': 'INTERNA', 'collapse_sidebar': 'Contraer barra lateral (Ctrl+[)', 'expand_sidebar': 'Expandir barra lateral (Ctrl+[)', 'split_screen': 'Alternar pantalla dividida (Ctrl+\\)', 'downloads': 'Descargas (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Alternar asistente de IA y notas (Ctrl+B)', 'keybinds_tooltip': 'Abrir paleta de comandos y atajos (Ctrl+K)', 'settings_tooltip': 'Abrir ajustes e importador (Ctrl+,)', 'vertical_btn': 'VERTICAL', 'ai_chat_tab': 'CHAT IA', 'scratchpad_tab': 'NOTAS', 'select_container': 'Abrir en contenedor de perfil...'}, 'de': {'app_title': 'Zephyrium', 'new_tab': 'Neuer Tab', 'close_tab': 'Tab schließen', 'duplicate_tab': 'Tab duplizieren', 'split_view': 'Geteilter Bildschirm', 'suspend_tab': 'Tab anhalten (RAM freigeben)', 'wake_tab': 'Tab wiederherstellen', 'tab_suspended_title': 'TAB ANGEHALTEN // RAM GESPEICHERT', 'tab_suspended_hint': 'Klicken Sie auf den Tab, um die Sitzung wiederherzustellen.', 'mode_minimal': 'Minimalistisch', 'mode_vim': 'Vim-Modus (rahmenlos)', 'tab_orientation': 'Tab-Ausrichtung', 'vertical_tabs': 'Vertikale Tabs (Seitenleiste)', 'horizontal_tabs': 'Horizontale Tabs (obere Leiste)', 'switch_to_vertical': 'Zu vertikalen Tabs wechseln', 'switch_to_horizontal': 'Zu horizontalen Tabs wechseln', 'exit_vim': 'VIM BEENDEN', 'vim_hint': "[VIM NORMAL] Drücken Sie ':' oder 'o' für Befehle | '?' für Hilfe", 'adblock_blocked': 'Blockierte Werbung: {count}', 'adblock_whitelist': "Domain '{domain}' zur Whitelist hinzufügen", 'adblock_unwhitelist': "'{domain}' von Whitelist entfernen", 'clean_url': 'Tracking-Parameter aus URL entfernen', 'tor_proxy': 'Tor-Proxy (SOCKS5 9050): {status}', 'settings': 'Einstellungen & Konfiguration', 'general': 'Allgemein', 'privacy': 'Datenschutz & Werbeblocker', 'import': 'Daten importieren', 'vault': 'Passwörter & Cookies', 'appearance': 'Erscheinungsbild & Modi', 'ai_assistant': 'KI-Assistent', 'network': 'Netzwerk & Erweitert', 'about': 'Über', 'vault_locked_title': 'ANMELDEDATEN-TRESOR // GESCHÜTZT', 'vault_locked_desc': 'Das Anzeigen und Exportieren erfordert Superuser-Berechtigung (sudo).', 'sudo_password_label': 'Sudo-Passwort eingeben:', 'unlock_vault': 'Tresor entsperren', 'lock_vault': 'Sperren', 'wrong_sudo_password': 'Authentifizierung fehlgeschlagen. Falsches Passwort.', 'passwords': 'Passwörter', 'cookies': 'Cookies', 'export_csv': 'Als CSV exportieren', 'export_json': 'Als JSON exportieren', 'export_netscape': 'Netscape TXT exportieren', 'add_credential': 'Anmeldedaten hinzufügen', 'domain': 'Domain / URL', 'username': 'Benutzername', 'password': 'Passwort', 'actions': 'Aktionen', 'copy_login': 'Benutzername kopieren', 'copy_password': 'Passwort kopieren', 'copied': 'In die Zwischenablage kopiert!', 'search_cookies': 'Cookies filtern...', 'save_settings': 'Einstellungen speichern', 'cancel': 'Abbrechen', 'language': 'Sprache', 'language_note': 'Anzeigesprache auswählen', 'homepage_url': 'Startseiten-URL:', 'search_engine': 'Standard-Suchmaschine:', 'downloads_dir': 'Download-Verzeichnis:', 'browse': 'DURCHSUCHEN', 'restore_tabs': 'Geöffnete Tabs beim Start wiederherstellen', 'enable_adblock': 'Integrierten Werbe- und Tracker-Blocker aktivieren', 'clean_urls_label': 'Tracking-Parameter (utm_*, fbclid) automatisch entfernen', 'send_dnt_label': "'Do Not Track'-Header (DNT: 1) senden", 'prevent_webrtc_label': 'WebRTC-IP-Leck verhindern', 'whitelist_title': 'Freigegebene Domains (Filterung umgehen):', 'add_domain_btn': '+ DOMAIN HINZUFÜGEN', 'remove_domain_btn': 'AUSGEWÄHLTE DOMAIN ENTFERNEN', 'select_browser_import': 'Installierten Browser für den Import auswählen:', 'custom_profile_dir': 'Oder benutzerdefiniertes Profilverzeichnis angeben:', 'items_to_import': 'Zu importierende Elemente:', 'bookmarks': 'Lesezeichen', 'history': 'Verlauf', 'start_import_btn': 'MIGRATION / IMPORT STARTEN', 'import_csv_btn': 'PASSWÖRTER AUS CSV IMPORTIEREN...', 'show': 'ZEIGEN', 'copy': 'KOPIEREN', 'color_theme': 'Farbthema:', 'theme_dark': 'Minimalistisch Dunkel', 'theme_light': 'Helles Papier (Paper)', 'primary_accent': 'Primäre Akzentfarbe:', 'ui_mode_label': 'UI-Modus:', 'font_family_label': 'Monospace-Schriftart:', 'font_size_label': 'UI-Basisschriftgröße (px):', 'sidebar_width_label': 'Breite der Tab-Seitenleiste (px):', 'gemini_key_label': 'Gemini-API-Schlüssel (Live-Inferenz):', 'ai_model_label': 'KI-Modellauswahl:', 'fetch_models_btn': 'VERFÜGBARE MODELLE ABRUFEN', 'ai_persona_label': 'Systemanweisung / KI-Persona:', 'enable_gpu': 'Hardwarebeschleunigung aktivieren (GPU-Rasterung)', 'proxy_server_label': 'SOCKS5 / HTTP Proxy-Server:', 'about_title': 'Über Zephyrium', 'save_apply_btn': 'SPEICHERN UND ANWENDEN', 'adblock_title': 'WERBUNG', 'split_title': 'SPLIT', 'downloads_title': 'DL', 'ai_title': 'KI', 'tabs_vert_short': 'TABS: VERT', 'tabs_horiz_short': 'TABS: HORIZ', 'mode_label': 'MODUS', 'keybinds': 'HOTKEYS', 'settings_btn': 'SETUP', 'new_tab_btn': '+ NEUER TAB', 'profile_btn': 'PROFIL', 'url_placeholder': 'DuckDuckGo-Suche oder URL eingeben... (oder Strg+K)', 'ready': 'BEREIT', 'loading_status': 'LADEN {progress}%...', 'settings_saved_msg': 'Einstellungen gespeichert und angewendet.', 'internal_page': 'INTERN', 'collapse_sidebar': 'Seitenleiste einklappen (Ctrl+[)', 'expand_sidebar': 'Seitenleiste ausklappen (Ctrl+[)', 'split_screen': 'Geteilten Bildschirm umschalten (Ctrl+\\)', 'downloads': 'Downloads (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'KI-Assistent & Notizen (Ctrl+B)', 'keybinds_tooltip': 'Befehlspalette & Hotkeys öffnen (Ctrl+K)', 'settings_tooltip': 'Einstellungen & Datenimport (Ctrl+,)', 'vertical_btn': 'VERTIKAL', 'ai_chat_tab': 'KI-CHAT', 'scratchpad_tab': 'NOTIZEN', 'select_container': 'In Profil-Container öffnen...'}, 'fr': {'app_title': 'Zephyrium', 'new_tab': 'Nouvel onglet', 'close_tab': "Fermer l'onglet", 'duplicate_tab': "Dupliquer l'onglet", 'split_view': 'Écran partagé', 'suspend_tab': "Suspendre l'onglet (Libérer la RAM)", 'wake_tab': "Restaurer l'onglet", 'tab_suspended_title': 'ONGLET SUSPENDU // RAM LIBÉRÉE', 'tab_suspended_hint': "Cliquez sur l'onglet pour restaurer la session.", 'mode_minimal': 'Minimaliste', 'mode_vim': 'Mode Vim (sans cadre)', 'tab_orientation': 'Orientation des onglets', 'vertical_tabs': 'Onglets verticaux (barre latérale)', 'horizontal_tabs': 'Onglets horizontaux (barre supérieure)', 'switch_to_vertical': 'Passer aux onglets verticaux', 'switch_to_horizontal': 'Passer aux onglets horizontaux', 'exit_vim': 'QUITTER VIM', 'vim_hint': "[VIM NORMAL] Appuyez sur ':' ou 'o' pour les commandes | '?' pour l'aide", 'adblock_blocked': 'Publicités bloquées: {count}', 'adblock_whitelist': "Ajouter '{domain}' à la liste blanche", 'adblock_unwhitelist': "Retirer '{domain}' de la liste blanche", 'clean_url': "Nettoyer les paramètres de suivi de l'URL", 'tor_proxy': 'Proxy Tor (SOCKS5 9050): {status}', 'settings': 'Paramètres & Configuration', 'general': 'Général', 'privacy': 'Confidentialité & Bloqueur', 'import': 'Importer des données', 'vault': 'Mots de passe & Cookies', 'appearance': 'Apparence & Modes', 'ai_assistant': 'Assistant IA', 'network': 'Réseau & Avancé', 'about': 'À propos', 'vault_locked_title': "COFFRE D'IDENTIFIANTS // PROTÉGÉ", 'vault_locked_desc': "L'affichage et l'exportation nécessitent une autorisation superutilisateur (sudo).", 'sudo_password_label': 'Entrez le mot de passe sudo:', 'unlock_vault': 'Déverrouiller le coffre', 'lock_vault': 'Verrouiller', 'wrong_sudo_password': "Échec d'authentification. Mot de passe incorrect.", 'passwords': 'Mots de passe', 'cookies': 'Cookies', 'export_csv': 'Exporter en CSV', 'export_json': 'Exporter en JSON', 'export_netscape': 'Exporter Netscape TXT', 'add_credential': 'Ajouter un identifiant', 'domain': 'Domaine / URL', 'username': "Nom d'utilisateur", 'password': 'Mot de passe', 'actions': 'Actions', 'copy_login': "Copier l'identifiant", 'copy_password': 'Copier le mot de passe', 'copied': 'Copié dans le presse-papier !', 'search_cookies': 'Filtrer les cookies...', 'save_settings': 'Enregistrer les préférences', 'cancel': 'Annuler', 'language': 'Langue', 'language_note': "Sélectionnez la langue d'affichage", 'homepage_url': "URL de page d'accueil:", 'search_engine': 'Moteur de recherche par défaut:', 'downloads_dir': 'Répertoire de téléchargement:', 'browse': 'PARCOURIR', 'restore_tabs': 'Restaurer les onglets ouverts au démarrage', 'enable_adblock': 'Activer le bloqueur de publicités et de traqueurs', 'clean_urls_label': 'Supprimer automatiquement les balises de suivi (utm_*, fbclid)', 'send_dnt_label': "Envoyer l'en-tête 'Do Not Track' (DNT: 1)", 'prevent_webrtc_label': "Empêcher les fuites d'adresse IP via WebRTC", 'whitelist_title': 'Domaines en liste blanche (ignorer le filtrage):', 'add_domain_btn': '+ AJOUTER UN DOMAINE', 'remove_domain_btn': 'SUPPRIMER LE DOMAINE SÉLECTIONNÉ', 'select_browser_import': 'Sélectionnez le navigateur à partir duquel importer:', 'custom_profile_dir': 'Ou spécifiez un répertoire de profil personnalisé:', 'items_to_import': 'Éléments à importer:', 'bookmarks': 'Favoris', 'history': 'Historique', 'start_import_btn': 'DÉMARRER LA MIGRATION / IMPORT', 'import_csv_btn': 'IMPORTER LES MOTS DE PASSE (CSV)...', 'show': 'AFFICHER', 'copy': 'COPIER', 'color_theme': 'Thème de couleur:', 'theme_dark': 'Sombre minimaliste', 'theme_light': 'Clair épuré (Papier)', 'primary_accent': "Couleur d'accent principale:", 'ui_mode_label': "Mode d'interface:", 'font_family_label': 'Police à chasse fixe:', 'font_size_label': 'Taille de police de base (px):', 'sidebar_width_label': "Largeur de la barre d'onglets (px):", 'gemini_key_label': 'Clé API Gemini (inférence en direct):', 'ai_model_label': "Sélection du modèle d'IA:", 'fetch_models_btn': 'CHARGER LES MODÈLES DISPONIBLES', 'ai_persona_label': "Instruction système / Persona d'IA:", 'enable_gpu': "Activer l'accélération matérielle (GPU)", 'proxy_server_label': 'Serveur proxy SOCKS5 / HTTP:', 'about_title': 'À propos de Zephyrium', 'save_apply_btn': 'ENREGISTRER ET APPLIQUER', 'adblock_title': 'PUB', 'split_title': 'SCINDÉ', 'downloads_title': 'TÉLÉCH', 'ai_title': 'IA', 'tabs_vert_short': 'ONGLETS: VERT', 'tabs_horiz_short': 'ONGLETS: HORIZ', 'mode_label': 'MODE', 'keybinds': 'TOUCHES', 'settings_btn': 'RÉGLAGES', 'new_tab_btn': '+ NOUVEL ONGLET', 'profile_btn': 'PROFIL', 'url_placeholder': 'Rechercher sur DuckDuckGo ou entrer une URL... (Ctrl+K)', 'ready': 'PRÊT', 'loading_status': 'CHARGEMENT {progress}%...', 'settings_saved_msg': 'Paramètres enregistrés et appliqués.', 'internal_page': 'INTERNE', 'collapse_sidebar': 'Réduire la barre latérale (Ctrl+[)', 'expand_sidebar': 'Développer la barre latérale (Ctrl+[)', 'split_screen': 'Basculer écran partagé (Ctrl+\\)', 'downloads': 'Téléchargements (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Basculer assistant IA et notes (Ctrl+B)', 'keybinds_tooltip': 'Ouvrir palette de commandes et raccourcis (Ctrl+K)', 'settings_tooltip': 'Ouvrir les paramètres et importateur (Ctrl+,)', 'vertical_btn': 'VERTICAL', 'ai_chat_tab': 'CHAT IA', 'scratchpad_tab': 'BLOC-NOTES', 'select_container': 'Ouvrir dans le conteneur de profil...'}, 'ja': {'app_title': 'Zephyrium', 'new_tab': '新しいタブ', 'close_tab': 'タブを閉じる', 'duplicate_tab': 'タブを複製', 'split_view': '画面分割', 'suspend_tab': 'タブを休止 (メモリ解放)', 'wake_tab': 'タブを復元', 'tab_suspended_title': 'タブ休止中 // メモリ解放済み', 'tab_suspended_hint': 'タブをクリックするとセッションが復元されます。', 'mode_minimal': 'ミニマル', 'mode_vim': 'Vimモード (枠なし)', 'tab_orientation': 'タブの配置方向', 'vertical_tabs': '垂直タブ (サイドバー)', 'horizontal_tabs': '水平タブ (上部バー)', 'switch_to_vertical': '垂直タブに切り替え', 'switch_to_horizontal': '水平タブに切り替え', 'exit_vim': 'VIMを終了', 'vim_hint': "[VIM NORMAL] ':' または 'o' でコマンド入力 | '?' でヘルプ", 'adblock_blocked': 'ブロック済み広告: {count}', 'adblock_whitelist': "ドメイン '{domain}' をホワイトリストに追加", 'adblock_unwhitelist': "'{domain}' をホワイトリストから削除", 'clean_url': 'URLからトラッキング変数を削除', 'tor_proxy': 'Torプロキシ (SOCKS5 9050): {status}', 'settings': '設定と構成', 'general': '一般', 'privacy': 'プライバシーとブロック', 'import': 'データのインポート', 'vault': 'パスワードとCookie', 'appearance': '外観とモード', 'ai_assistant': 'AIアシスタント', 'network': 'ネットワークと詳細設定', 'about': '情報', 'vault_locked_title': '認証情報保管庫 // 保護中', 'vault_locked_desc': 'パスワードとCookieの閲覧・エクスポートにはsudo権限が必要です。', 'sudo_password_label': 'sudoパスワードを入力:', 'unlock_vault': '保管庫のロック解除', 'lock_vault': 'ロック', 'wrong_sudo_password': '認証に失敗しました。パスワードが違います。', 'passwords': 'パスワード', 'cookies': 'Cookie', 'export_csv': 'CSV形式で出力', 'export_json': 'JSON形式で出力', 'export_netscape': 'Netscape形式で出力', 'add_credential': '認証情報を追加', 'domain': 'ドメイン / URL', 'username': 'ユーザー名', 'password': 'パスワード', 'actions': '操作', 'copy_login': 'ログインIDをコピー', 'copy_password': 'パスワードをコピー', 'copied': 'クリップボードにコピーしました！', 'search_cookies': 'ドメイン名でCookieを検索...', 'save_settings': '設定を保存', 'cancel': 'キャンセル', 'language': '言語', 'language_note': 'インターフェース表示言語を選択', 'homepage_url': 'ホームページURL:', 'search_engine': 'デフォルトの検索エンジン:', 'downloads_dir': 'ダウンロード先ディレクトリ:', 'browse': '参照', 'restore_tabs': '起動時に開いていたタブを復元', 'enable_adblock': '広告およびトラッカーのネイティブブロックを有効化', 'clean_urls_label': '追跡タグ (utm_*, fbclid等) をURLから自動削除', 'send_dnt_label': "すべてのリクエストで 'Do Not Track' (DNT: 1) を送信", 'prevent_webrtc_label': 'WebRTCによるIPアドレスの漏洩を防止', 'whitelist_title': 'ホワイトリスト登録ドメイン (フィルタ除外):', 'add_domain_btn': '+ ドメインを追加', 'remove_domain_btn': '選択したドメインを削除', 'select_browser_import': 'インポート元のブラウザを選択:', 'custom_profile_dir': 'またはプロファイルディレクトリを指定:', 'items_to_import': 'インポートする項目:', 'bookmarks': 'ブックマーク', 'history': '履歴', 'start_import_btn': '移行・インポートを開始', 'import_csv_btn': 'CSVからパスワードをインポート...', 'show': '表示', 'copy': 'コピー', 'color_theme': 'カラーテーマ:', 'theme_dark': 'ミニマルダーク', 'theme_light': 'クリーンライト (Paper)', 'primary_accent': 'プライマリアクセントカラー:', 'ui_mode_label': 'UIモード:', 'font_family_label': '等幅フォントファミリー:', 'font_size_label': 'UI基本フォントサイズ (px):', 'sidebar_width_label': '垂直タブサイドバーの幅 (px):', 'gemini_key_label': 'Gemini APIキー (リアルタイム推論):', 'ai_model_label': 'AIモデルの選択:', 'fetch_models_btn': '利用可能なモデルを取得', 'ai_persona_label': 'システム指示 / AIペルソナ:', 'enable_gpu': 'ハードウェアアクセラレーションを有効化 (GPU)', 'proxy_server_label': 'SOCKS5 / HTTP プロキシサーバー:', 'about_title': 'Zephyrium について', 'save_apply_btn': '保存して適用', 'adblock_title': '広告', 'split_title': '分割', 'downloads_title': 'DL', 'ai_title': 'AI', 'tabs_vert_short': 'タブ: 垂直', 'tabs_horiz_short': 'タブ: 水平', 'mode_label': 'モード', 'keybinds': 'キー設定', 'settings_btn': '設定', 'new_tab_btn': '+ 新規タブ', 'profile_btn': 'プロファイル', 'url_placeholder': 'DuckDuckGoで検索またはURLを入力... (Ctrl+K)', 'ready': '準備完了', 'loading_status': '読み込み中 {progress}%...', 'settings_saved_msg': '設定を保存して適用しました。', 'internal_page': '内部', 'collapse_sidebar': 'サイドバーを折りたたむ (Ctrl+[)', 'expand_sidebar': 'サイドバーを展開 (Ctrl+[)', 'split_screen': '画面分割の切り替え (Ctrl+\\)', 'downloads': 'ダウンロード (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'AIアシスタントとメモ (Ctrl+B)', 'keybinds_tooltip': 'コマンドパレットとキー設定 (Ctrl+K)', 'settings_tooltip': '設定とインポート (Ctrl+,)', 'vertical_btn': '垂直', 'ai_chat_tab': 'AIチャット', 'scratchpad_tab': 'スクラッチパッド', 'select_container': 'プロファイルコンテナで開く...'}, 'pt': {'app_title': 'Zephyrium', 'new_tab': 'Nova aba', 'close_tab': 'Fechar aba', 'duplicate_tab': 'Duplicar aba', 'split_view': 'Dividir tela', 'suspend_tab': 'Suspender aba (Liberar RAM)', 'wake_tab': 'Restaurar aba', 'tab_suspended_title': 'ABA SUSPENSA // RAM LIBERADA', 'tab_suspended_hint': 'Clique na aba para restaurar a sessão.', 'mode_minimal': 'Minimalista', 'mode_vim': 'Modo Vim (sem bordas)', 'tab_orientation': 'Orientação das abas', 'vertical_tabs': 'Abas verticais (barra lateral)', 'horizontal_tabs': 'Abas horizontais (barra superior)', 'switch_to_vertical': 'Mudar para abas verticais', 'switch_to_horizontal': 'Mudar para abas horizontais', 'exit_vim': 'SAIR DO VIM', 'vim_hint': "[VIM NORMAL] Pressione ':' ou 'o' para comandos | '?' para ajuda", 'adblock_blocked': 'Anúncios bloqueados: {count}', 'adblock_whitelist': "Adicionar '{domain}' à lista de permissões", 'adblock_unwhitelist': "Remover '{domain}' da lista de permissões", 'clean_url': 'Limpar parâmetros de rastreamento do URL', 'tor_proxy': 'Proxy Tor (SOCKS5 9050): {status}', 'settings': 'Configurações', 'general': 'Geral', 'privacy': 'Privacidade & Bloqueador', 'import': 'Importar dados', 'vault': 'Senhas e Cookies', 'appearance': 'Aparência & Modos', 'ai_assistant': 'Assistente IA', 'network': 'Rede & Avançado', 'about': 'Sobre', 'vault_locked_title': 'COFRE DE CREDENCIAIS // PROTEGIDO', 'vault_locked_desc': 'Visualizar e exportar senhas e cookies exige autorização de superusuário (sudo).', 'sudo_password_label': 'Digite a senha do sudo:', 'unlock_vault': 'Desbloquear cofre', 'lock_vault': 'Bloquear', 'wrong_sudo_password': 'Falha na autenticação. Senha incorreta.', 'passwords': 'Senhas', 'cookies': 'Cookies', 'export_csv': 'Exportar para CSV', 'export_json': 'Exportar para JSON', 'export_netscape': 'Exportar Netscape TXT', 'add_credential': 'Adicionar credencial', 'domain': 'Domínio / URL', 'username': 'Usuário', 'password': 'Senha', 'actions': 'Ações', 'copy_login': 'Copiar usuário', 'copy_password': 'Copiar senha', 'copied': 'Copiado para a área de transferência!', 'search_cookies': 'Filtrar cookies...', 'save_settings': 'Salvar preferências', 'cancel': 'Cancelar', 'language': 'Idioma', 'language_note': 'Selecione o idioma de exibição', 'homepage_url': 'URL da página inicial:', 'search_engine': 'Mecanismo de busca padrão:', 'downloads_dir': 'Diretório de downloads:', 'browse': 'PROCURAR', 'restore_tabs': 'Restaurar abas abertas ao iniciar', 'enable_adblock': 'Ativar bloqueador nativo de anúncios e rastreadores', 'clean_urls_label': 'Remover automaticamente parâmetros de rastreamento', 'send_dnt_label': "Enviar cabeçalho 'Do Not Track' (DNT: 1)", 'prevent_webrtc_label': 'Prevenir vazamento de endereço IP via WebRTC', 'whitelist_title': 'Domínios permitidos (ignorar filtragem):', 'add_domain_btn': '+ ADICIONAR DOMÍNIO', 'remove_domain_btn': 'REMOVER DOMÍNIO SELECIONADO', 'select_browser_import': 'Selecione o navegador para importar:', 'custom_profile_dir': 'Ou especifique o diretório de perfil personalizado:', 'items_to_import': 'Itens para importar:', 'bookmarks': 'Favoritos', 'history': 'Histórico', 'start_import_btn': 'INICIAR MIGRAÇÃO / IMPORTAÇÃO', 'import_csv_btn': 'IMPORTAR SENHAS DO CSV...', 'show': 'MOSTRAR', 'copy': 'COPIAR', 'color_theme': 'Tema de cor:', 'theme_dark': 'Escuro minimalista', 'theme_light': 'Claro limpo (Paper)', 'primary_accent': 'Cor de destaque principal:', 'ui_mode_label': 'Modo de interface:', 'font_family_label': 'Fonte monoespaçada:', 'font_size_label': 'Tamanho de fonte base (px):', 'sidebar_width_label': 'Largura da barra lateral de abas (px):', 'gemini_key_label': 'Chave da API Gemini (inferência ao vivo):', 'ai_model_label': 'Seleção do modelo de IA:', 'fetch_models_btn': 'BUSCAR MODELOS DISPONÍVEIS', 'ai_persona_label': 'Instrução de sistema / Persona da IA:', 'enable_gpu': 'Ativar aceleração de hardware (GPU)', 'proxy_server_label': 'Server proxy SOCKS5 / HTTP:', 'about_title': 'Sobre o Zephyrium', 'save_apply_btn': 'SALVAR E APLICAR', 'adblock_title': 'ANÚNCIOS', 'split_title': 'DIVIDIR', 'downloads_title': 'DOWN', 'ai_title': 'IA', 'tabs_vert_short': 'ABAS: VERT', 'tabs_horiz_short': 'ABAS: HORIZ', 'mode_label': 'MODO', 'keybinds': 'ATALHOS', 'settings_btn': 'CONFIG', 'new_tab_btn': '+ NOVA ABA', 'profile_btn': 'PERFIL', 'url_placeholder': 'Pesquisar no DuckDuckGo ou digitar URL... (Ctrl+K)', 'ready': 'PRONTO', 'loading_status': 'CARREGANDO {progress}%...', 'settings_saved_msg': 'Configurações salvas e aplicadas.', 'internal_page': 'INTERNA', 'collapse_sidebar': 'Recolher barra lateral (Ctrl+[)', 'expand_sidebar': 'Expandir barra lateral (Ctrl+[)', 'split_screen': 'Alternar tela dividida (Ctrl+\\)', 'downloads': 'Downloads (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Alternar assistente de IA e notas (Ctrl+B)', 'keybinds_tooltip': 'Abrir paleta de comandos e atalhos (Ctrl+K)', 'settings_tooltip': 'Abrir configurações e importador (Ctrl+,)', 'vertical_btn': 'VERTICAL', 'ai_chat_tab': 'CHAT IA', 'scratchpad_tab': 'NOTAS', 'select_container': 'Abrir no contêiner de perfil...'}, 'it': {'app_title': 'Zephyrium', 'new_tab': 'Nuova scheda', 'close_tab': 'Chiudi scheda', 'duplicate_tab': 'Duplica scheda', 'split_view': 'Schermo diviso', 'suspend_tab': 'Sospendi scheda (Libera RAM)', 'wake_tab': 'Ripristina scheda', 'tab_suspended_title': 'SCHEDA SOSPESA // RAM LIBERATA', 'tab_suspended_hint': 'Fai clic sulla scheda per ripristinare la sessione.', 'mode_minimal': 'Minimalista', 'mode_vim': 'Modalità Vim (senza cornici)', 'tab_orientation': 'Orientamento schede', 'vertical_tabs': 'Schede verticali (barra laterale)', 'horizontal_tabs': 'Schede orizzontali (barra superiore)', 'switch_to_vertical': 'Passa alle schede verticali', 'switch_to_horizontal': 'Passa alle schede orizzontali', 'exit_vim': 'ESCI DA VIM', 'vim_hint': "[VIM NORMALE] Premi ':' o 'o' per i comandi | '?' per aiuto", 'adblock_blocked': 'Annunci bloccati: {count}', 'adblock_whitelist': "Aggiungi '{domain}' alla whitelist", 'adblock_unwhitelist': "Rimuovi '{domain}' dalla whitelist", 'clean_url': "Pulisci parametri di tracciamento dall'URL", 'tor_proxy': 'Proxy Tor (SOCKS5 9050): {status}', 'settings': 'Impostazioni e configurazione', 'general': 'Generale', 'privacy': 'Privacy & Blocco annunci', 'import': 'Importa dati', 'vault': 'Password e Cookie', 'appearance': 'Aspetto e modalità', 'ai_assistant': 'Assistente IA', 'network': 'Rete e avanzate', 'about': 'Informazioni', 'vault_locked_title': 'CASSAFORTE CREDENZIALI // PROTETTA', 'vault_locked_desc': "La visualizzazione e l'esportazione richiedono l'autorizzazione superuser (sudo).", 'sudo_password_label': 'Inserisci la password sudo:', 'unlock_vault': 'Sblocca cassaforte', 'lock_vault': 'Blocca', 'wrong_sudo_password': 'Autenticazione fallita. Password errata.', 'passwords': 'Password', 'cookies': 'Cookie', 'export_csv': 'Esporta in CSV', 'export_json': 'Esporta in JSON', 'export_netscape': 'Esporta Netscape TXT', 'add_credential': 'Aggiungi credenziale', 'domain': 'Dominio / URL', 'username': 'Nome utente', 'password': 'Password', 'actions': 'Azioni', 'copy_login': 'Copia utente', 'copy_password': 'Copia password', 'copied': 'Copiato negli appunti!', 'search_cookies': 'Filtra cookie...', 'save_settings': 'Salva preferenze', 'cancel': 'Annulla', 'language': 'Lingua', 'language_note': 'Seleziona la lingua di visualizzazione', 'homepage_url': 'URL pagina iniziale:', 'search_engine': 'Motore di ricerca predefinito:', 'downloads_dir': 'Cartella download:', 'browse': 'SFOGLIA', 'restore_tabs': "Ripristina schede aperte all'avvio", 'enable_adblock': 'Abilita blocco annunci e tracker nativo', 'clean_urls_label': 'Rimuovi automaticamente i tag di tracciamento (utm_*, fbclid)', 'send_dnt_label': "Invia intestazione 'Do Not Track' (DNT: 1)", 'prevent_webrtc_label': "Previeni leak dell'indirizzo IP via WebRTC", 'whitelist_title': 'Domini in whitelist (ignora filtraggio):', 'add_domain_btn': '+ AGGIUNGI DOMINIO', 'remove_domain_btn': 'RIMUOVI DOMINIO SELEZIONATO', 'select_browser_import': 'Seleziona il browser da cui importare:', 'custom_profile_dir': 'Oppure specifica la cartella del profilo:', 'items_to_import': 'Elementi da importare:', 'bookmarks': 'Segnalibri', 'history': 'Cronologia', 'start_import_btn': 'AVVIA MIGRAZIONE / IMPORTAZIONE', 'import_csv_btn': 'IMPORTA PASSWORD DA CSV...', 'show': 'MOSTRA', 'copy': 'COPIA', 'color_theme': 'Tema colori:', 'theme_dark': 'Scuro minimalista', 'theme_light': 'Chiaro pulito (Paper)', 'primary_accent': 'Colore accento principale:', 'ui_mode_label': 'Modalità interfaccia:', 'font_family_label': 'Carattere a spaziatura fissa:', 'font_size_label': 'Dimensione carattere base (px):', 'sidebar_width_label': 'Larghezza barra laterale schede (px):', 'gemini_key_label': 'Chiave API Gemini (inferenza in tempo reale):', 'ai_model_label': 'Selezione modello IA:', 'fetch_models_btn': 'RECUPERA MODELLI DISPONIBILI', 'ai_persona_label': 'Istruzione di sistema / Persona IA:', 'enable_gpu': 'Abilita accelerazione hardware (GPU)', 'proxy_server_label': 'Server proxy SOCKS5 / HTTP:', 'about_title': 'Informazioni su Zephyrium', 'save_apply_btn': 'SALVA E APPLICA', 'adblock_title': 'ANNUNCI', 'split_title': 'DIVIDI', 'downloads_title': 'DOWN', 'ai_title': 'IA', 'tabs_vert_short': 'SCHEDE: VERT', 'tabs_horiz_short': 'SCHEDE: ORIZZ', 'mode_label': 'MODO', 'keybinds': 'TASTI', 'settings_btn': 'OPZIONI', 'new_tab_btn': '+ SCHEDA', 'profile_btn': 'PROFILO', 'url_placeholder': 'Cerca su DuckDuckGo o inserisci URL... (Ctrl+K)', 'ready': 'PRONTO', 'loading_status': 'CARICAMENTO {progress}%...', 'settings_saved_msg': 'Impostazioni salvate e applicate.', 'internal_page': 'INTERNO', 'collapse_sidebar': 'Comprimi barra laterale (Ctrl+[)', 'expand_sidebar': 'Espandi barra laterale (Ctrl+[)', 'split_screen': 'Attiva/disattiva schermo diviso (Ctrl+\\)', 'downloads': 'Download (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Attiva/disattiva assistente IA e note (Ctrl+B)', 'keybinds_tooltip': 'Apri comandi e tasti (Ctrl+K)', 'settings_tooltip': 'Apri impostazioni e importatore (Ctrl+,)', 'vertical_btn': 'VERTICALE', 'ai_chat_tab': 'CHAT IA', 'scratchpad_tab': 'APPUNTI', 'select_container': 'Apri nel contenitore del profilo...'}, 'tr': {'app_title': 'Zephyrium', 'new_tab': 'Yeni Sekme', 'close_tab': 'Sekmeyi Kapat', 'duplicate_tab': 'Sekmeyi Çoğalt', 'split_view': 'Bölünmüş Ekran', 'suspend_tab': 'Sekmeyi Askıya Al (RAM Boşalt)', 'wake_tab': 'Sekmeyi Geri Yükle', 'tab_suspended_title': 'SEKME ASKIYA ALINDI // RAM KORUNDU', 'tab_suspended_hint': 'Oturumu geri yüklemek için sekmeye tıklayın.', 'mode_minimal': 'Minimal', 'mode_vim': 'Vim Modu (çerçevesiz)', 'tab_orientation': 'Sekme Yerleşim Yönü', 'vertical_tabs': 'Dikey Sekmeler (Kenar Çubuğu)', 'horizontal_tabs': 'Yatay Sekmeler (Üst Çubuk)', 'switch_to_vertical': 'Dikey Sekmelere Geç', 'switch_to_horizontal': 'Yatay Sekmelere Geç', 'exit_vim': "VİM'DEN ÇIK", 'vim_hint': "[VIM NORMAL] Komutlar için ':' veya 'o' | Yardım için '?'", 'adblock_blocked': 'Engellenen reklamlar: {count}', 'adblock_whitelist': "'{domain}' alan adını beyaz listeye ekle", 'adblock_unwhitelist': "'{domain}' alan adını beyaz listeden kaldır", 'clean_url': "URL'den izleme parametrelerini temizle", 'tor_proxy': 'Tor Vekil Sunucusu (SOCKS5 9050): {status}', 'settings': 'Ayarlar ve Yapılandırma', 'general': 'Genel', 'privacy': 'Gizlilik ve Reklam Engelleyici', 'import': 'Veri İçe Aktar', 'vault': 'Şifreler ve Çerezler', 'appearance': 'Görünüm ve Modlar', 'ai_assistant': 'Yapay Zeka Asistanı', 'network': 'Ağ ve Gelişmiş', 'about': 'Hakkında', 'vault_locked_title': 'KİMLİK BİLGİSİ KASASI // KORUMALI', 'vault_locked_desc': 'Kayıtlı şifreleri ve çerezleri görüntülemek süper kullanıcı (sudo) yetkilendirmesi gerektirir.', 'sudo_password_label': 'Sudo şifresini girin:', 'unlock_vault': 'Kasanın Kilidini Aç', 'lock_vault': 'Kilitle', 'wrong_sudo_password': 'Kimlik doğrulama başarısız oldu. Yanlış şifre.', 'passwords': 'Şifreler', 'cookies': 'Çerezler', 'export_csv': 'CSV Olarak Dışa Aktar', 'export_json': 'JSON Olarak Dışa Aktar', 'export_netscape': 'Netscape TXT Dışa Aktar', 'add_credential': 'Yeni Kimlik Bilgisi Ekle', 'domain': 'Alan Adı / URL', 'username': 'Kullanıcı Adı', 'password': 'Şifre', 'actions': 'Eylemler', 'copy_login': 'Kullanıcıyı Kopyala', 'copy_password': 'Şifreyi Kopyala', 'copied': 'Panoya kopyalandı!', 'search_cookies': 'Çerezleri filtrele...', 'save_settings': 'Ayarları Kaydet', 'cancel': 'İptal', 'language': 'Arayüz Dili', 'language_note': 'Tarayıcı görüntüleme dilini seçin', 'homepage_url': "Ana Sayfa URL'si:", 'search_engine': 'Varsayılan Arama Motoru:', 'downloads_dir': 'İndirmeler Dizini:', 'browse': 'GÖZAT', 'restore_tabs': 'Başlangıçta açık sekmeleri geri yükle', 'enable_adblock': 'Yerleşik Ağ Reklam ve Takipçi Engelleyiciyi Etkinleştir', 'clean_urls_label': 'İzleme etiketlerini (utm_*, fbclid) otomatik temizle', 'send_dnt_label': "Tüm isteklerde 'Do Not Track' (DNT: 1) başlığı gönder", 'prevent_webrtc_label': 'WebRTC IP Adresi Sızıntısını Önle', 'whitelist_title': 'İzin Verilen Alan Adları (Filtreyi Atla):', 'add_domain_btn': '+ ALAN ADI EKLE', 'remove_domain_btn': 'SEÇİLİ ALAN ADINI KALDIR', 'select_browser_import': 'İçe aktarılacak tarayıcıyı seçin:', 'custom_profile_dir': 'Veya özel profil dizini belirtin:', 'items_to_import': 'İçe aktarılacak öğeler:', 'bookmarks': 'Yer İmleri', 'history': 'Geçmiş', 'start_import_btn': 'GÖÇÜ / İÇE AKTARMAYI BAŞLAT', 'import_csv_btn': "CSV'DEN PAROLALARI İÇE AKTAR...", 'show': 'GÖSTER', 'copy': 'KOPYALA', 'color_theme': 'Renk Teması:', 'theme_dark': 'Minimal Koyu', 'theme_light': 'Açık Tema (Kağıt)', 'primary_accent': 'Birincil Vurgu Rengi:', 'ui_mode_label': 'Arayüz Modu:', 'font_family_label': 'Eşaralıklı Yazı Tipi Ailesi:', 'font_size_label': 'Temel Yazı Tipi Boyutu (px):', 'sidebar_width_label': 'Dikey Sekmeler Kenar Çubuğu Genişliği (px):', 'gemini_key_label': 'Gemini API Anahtarı (Canlı Çıkarım):', 'ai_model_label': 'Yapay Zeka Modeli Seçimi:', 'fetch_models_btn': 'MEVCUT MODELLERİ GETİR', 'ai_persona_label': 'Sistem Yönergesi / Yapay Zeka Kişiliği:', 'enable_gpu': 'Donanım Hızlandırmayı Etkinleştir (GPU)', 'proxy_server_label': 'SOCKS5 / HTTP Proxy Sunucusu:', 'about_title': 'Zephyrium Hakkında', 'save_apply_btn': 'KAYDET VE UYGULA', 'adblock_title': 'REKLAM', 'split_title': 'BÖL', 'downloads_title': 'İNDİR', 'ai_title': 'YZ', 'tabs_vert_short': 'SEKME: DİKEY', 'tabs_horiz_short': 'SEKME: YATAY', 'mode_label': 'MOD', 'keybinds': 'TUŞLAR', 'settings_btn': 'AYARLAR', 'new_tab_btn': '+ YENİ SEKME', 'profile_btn': 'PROFİL', 'url_placeholder': "DuckDuckGo'da ara veya URL girin... (Ctrl+K)", 'ready': 'HAZIR', 'loading_status': 'YÜKLENİYOR {progress}%...', 'settings_saved_msg': 'Ayarlar kaydedildi ve uygulandı.', 'internal_page': 'DAHİLİ', 'collapse_sidebar': 'Kenar çubuğunu daralt (Ctrl+[)', 'expand_sidebar': 'Kenar çubuğunu genişlet (Ctrl+[)', 'split_screen': 'Bölünmüş ekranı aç/kapat (Ctrl+\\)', 'downloads': 'İndirmeler (Ctrl+Shift+D)', 'ai_assistant_tooltip': 'Yapay zeka asistanı ve notlar (Ctrl+B)', 'keybinds_tooltip': 'Komut paletini ve kısayolları aç (Ctrl+K)', 'settings_tooltip': 'Ayarlar ve içe aktarmayı aç (Ctrl+,)', 'vertical_btn': 'DİKEY', 'ai_chat_tab': 'YZ SOHBET', 'scratchpad_tab': 'NOT DEFTERİ', 'select_container': 'Profil kapsayıcısında aç...'}}

EXTRA_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'en': {
        'history_title': 'HISTORY',
        'open_full_history': 'Open Full History (zephyrium://history)',
        'clear_history': 'Clear Browsing History',
        'open_all_downloads': 'All Downloads (zephyrium://downloads)',
        'open_downloads_folder': 'Open Downloads Folder',
        'clear_downloads': 'Clear Downloads List',
        'downloads_settings': 'Download Settings...',
        'history_settings': 'History Settings...',
        'ai_online': 'ONLINE',
        'ai_no_key': 'NO KEY',
        'ai_thinking': 'THINKING...',
        'key_btn': 'KEY',
        'summarize_page': 'SUMMARIZE PAGE',
        'clear_chat': 'CLEAR',
        'run_btn': 'RUN',
        'ai_input_placeholder': 'Ask Zephyrium AI, @page <q>, or /help...',
        'ai_init_msg': 'Zephyrium AI Assistant initialized. Live Gemini inference is active.',
        'ai_chat_tab': 'AI CHAT',
        'scratchpad_tab': 'SCRATCHPAD',
        'adblock_settings_tab': 'AdBlock Settings & Whitelist...',
        'no_downloads': 'No downloads yet',
        'no_history': 'No history entries yet',
        'container_default': 'Default',
        'container_work': 'Work',
        'container_personal': 'Personal',
        'container_dev': 'Dev',
        'container_incognito': 'Incognito',
    },
    'ru': {
        'history_title': 'ЖУРНАЛ',
        'open_full_history': 'Открыть весь журнал (zephyrium://history)',
        'clear_history': 'Очистить историю посещений',
        'open_all_downloads': 'Все загрузки (zephyrium://downloads)',
        'open_downloads_folder': 'Открыть папку загрузок',
        'clear_downloads': 'Очистить список загрузок',
        'downloads_settings': 'Настройки загрузок...',
        'history_settings': 'Настройки журнала...',
        'ai_online': 'ОНЛАЙН',
        'ai_no_key': 'НЕТ КЛЮЧА',
        'ai_thinking': 'ДУМАЕТ...',
        'key_btn': 'КЛЮЧ',
        'summarize_page': 'КРАТКО О СТРАНИЦЕ',
        'clear_chat': 'ОЧИСТИТЬ',
        'run_btn': 'ОТПРАВИТЬ',
        'ai_input_placeholder': 'Спросить Zephyrium AI, @page <вопрос> или /help...',
        'ai_init_msg': 'AI-ассистент Zephyrium инициализирован. Инференс Gemini активен.',
        'ai_chat_tab': 'AI ЧАТ',
        'scratchpad_tab': 'ЗАМЕТКИ',
        'adblock_settings_tab': 'Настройки AdBlock и белый список...',
        'no_downloads': 'Загрузок пока нет',
        'no_history': 'Журнал пока пуст',
        'container_default': 'Основной',
        'container_work': 'Работа',
        'container_personal': 'Личный',
        'container_dev': 'Разработка',
        'container_incognito': 'Инкогнито',
    },
    'zh': {
        'history_title': '历史记录',
        'open_full_history': '打开完整历史 (zephyrium://history)',
        'clear_history': '清除浏览历史',
        'open_all_downloads': '所有下载 (zephyrium://downloads)',
        'open_downloads_folder': '打开下载文件夹',
        'clear_downloads': '清空下载列表',
        'downloads_settings': '下载设置...',
        'history_settings': '历史记录设置...',
        'ai_online': '在线',
        'ai_no_key': '无密钥',
        'ai_thinking': '思考中...',
        'key_btn': '密钥',
        'summarize_page': '总结页面',
        'clear_chat': '清除对话',
        'run_btn': '发送',
        'ai_input_placeholder': '向 Zephyrium AI 提问, @page <问题> 或 /help...',
        'ai_init_msg': 'Zephyrium AI 助手已就绪。实时 Gemini 推理已启用。',
        'ai_chat_tab': 'AI 对话',
        'scratchpad_tab': '便签本',
        'adblock_settings_tab': '广告拦截设置与白名单...',
        'no_downloads': '暂无下载项目',
        'no_history': '暂无历史记录',
        'container_default': '默认',
        'container_work': '工作',
        'container_personal': '个人',
        'container_dev': '开发',
        'container_incognito': '无痕',
    },
    'es': {
        'history_title': 'HISTORIAL',
        'open_full_history': 'Abrir historial completo (zephyrium://history)',
        'clear_history': 'Borrar historial',
        'open_all_downloads': 'Todas las descargas (zephyrium://downloads)',
        'open_downloads_folder': 'Abrir carpeta de descargas',
        'clear_downloads': 'Limpiar lista de descargas',
        'downloads_settings': 'Ajustes de descargas...',
        'history_settings': 'Ajustes del historial...',
        'ai_online': 'EN LÍNEA',
        'ai_no_key': 'SIN CLAVE',
        'ai_thinking': 'PENSANDO...',
        'key_btn': 'CLAVE',
        'summarize_page': 'RESUMIR PÁGINA',
        'clear_chat': 'LIMPIAR',
        'run_btn': 'ENVIAR',
        'ai_input_placeholder': 'Preguntar a Zephyrium AI, @page <pregunta>...',
        'ai_init_msg': 'Asistente de IA Zephyrium inicializado. Inferencia de Gemini activa.',
        'ai_chat_tab': 'CHAT IA',
        'scratchpad_tab': 'NOTAS',
        'adblock_settings_tab': 'Ajustes de AdBlock y lista blanca...',
        'no_downloads': 'Sin descargas aún',
        'no_history': 'Sin historial aún',
        'container_default': 'Predeterminado',
        'container_work': 'Trabajo',
        'container_personal': 'Personal',
        'container_dev': 'Desarrollo',
        'container_incognito': 'Incógnito',
    },
    'de': {
        'history_title': 'VERLAUF',
        'open_full_history': 'Vollständigen Verlauf öffnen (zephyrium://history)',
        'clear_history': 'Verlauf löschen',
        'open_all_downloads': 'Alle Downloads (zephyrium://downloads)',
        'open_downloads_folder': 'Download-Ordner öffnen',
        'clear_downloads': 'Download-Liste leeren',
        'downloads_settings': 'Download-Einstellungen...',
        'history_settings': 'Verlauf-Einstellungen...',
        'ai_online': 'ONLINE',
        'ai_no_key': 'KEIN SCHLÜSSEL',
        'ai_thinking': 'DENKT NACH...',
        'key_btn': 'SCHLÜSSEL',
        'summarize_page': 'SEITE ZUSAMMENFASSEN',
        'clear_chat': 'LEEREN',
        'run_btn': 'SENDEN',
        'ai_input_placeholder': 'Zephyrium KI fragen, @page <Frage>...',
        'ai_init_msg': 'Zephyrium KI-Assistent initialisiert. Gemini-Inferenz ist aktiv.',
        'ai_chat_tab': 'KI-CHAT',
        'scratchpad_tab': 'NOTIZEN',
        'adblock_settings_tab': 'AdBlock-Einstellungen & Whitelist...',
        'no_downloads': 'Noch keine Downloads',
        'no_history': 'Noch kein Verlauf',
        'container_default': 'Standard',
        'container_work': 'Arbeit',
        'container_personal': 'Persönlich',
        'container_dev': 'Entwicklung',
        'container_incognito': 'Inkognito',
    },
    'fr': {
        'history_title': 'HISTORIQUE',
        'open_full_history': "Ouvrir l'historique complet (zephyrium://history)",
        'clear_history': "Effacer l'historique",
        'open_all_downloads': 'Tous les téléchargements (zephyrium://downloads)',
        'open_downloads_folder': 'Ouvrir le dossier des téléchargements',
        'clear_downloads': 'Effacer la liste des téléchargements',
        'downloads_settings': 'Paramètres de téléchargement...',
        'history_settings': "Paramètres d'historique...",
        'ai_online': 'EN LIGNE',
        'ai_no_key': 'PAS DE CLÉ',
        'ai_thinking': 'RÉFLEXION...',
        'key_btn': 'CLÉ',
        'summarize_page': 'RÉSUMER LA PAGE',
        'clear_chat': 'EFFACER',
        'run_btn': 'ENVOYER',
        'ai_input_placeholder': 'Demander à Zephyrium IA, @page <question>...',
        'ai_init_msg': 'Assistant IA Zephyrium initialisé. Inférence Gemini active.',
        'ai_chat_tab': 'CHAT IA',
        'scratchpad_tab': 'BLOC-NOTES',
        'adblock_settings_tab': "Paramètres d'AdBlock et liste blanche...",
        'no_downloads': 'Aucun téléchargement',
        'no_history': 'Aucun historique',
        'container_default': 'Défaut',
        'container_work': 'Travail',
        'container_personal': 'Personnel',
        'container_dev': 'Développement',
        'container_incognito': 'Navigation privée',
    },
    'ja': {
        'history_title': '履歴',
        'open_full_history': '履歴をすべて表示 (zephyrium://history)',
        'clear_history': '閲覧履歴を消去',
        'open_all_downloads': 'すべてのダウンロード (zephyrium://downloads)',
        'open_downloads_folder': 'ダウンロードフォルダを開く',
        'clear_downloads': 'ダウンロード履歴を消去',
        'downloads_settings': 'ダウンロード設定...',
        'history_settings': '履歴設定...',
        'ai_online': 'オンライン',
        'ai_no_key': 'キーなし',
        'ai_thinking': '思考中...',
        'key_btn': 'キー',
        'summarize_page': 'ページを要約',
        'clear_chat': 'クリア',
        'run_btn': '実行',
        'ai_input_placeholder': 'Zephyrium AIに質問、@page <質問>...',
        'ai_init_msg': 'Zephyrium AI アシスタント準備完了。Gemini 推論有効。',
        'ai_chat_tab': 'AIチャット',
        'scratchpad_tab': 'スクラッチパッド',
        'adblock_settings_tab': '広告ブロック設定とホワイトリスト...',
        'no_downloads': 'ダウンロードはありません',
        'no_history': '履歴はありません',
        'container_default': 'デフォルト',
        'container_work': '仕事',
        'container_personal': 'プライベート',
        'container_dev': '開発',
        'container_incognito': 'シークレット',
    },
    'pt': {
        'history_title': 'HISTÓRICO',
        'open_full_history': 'Abrir histórico completo (zephyrium://history)',
        'clear_history': 'Limpar histórico',
        'open_all_downloads': 'Todos os downloads (zephyrium://downloads)',
        'open_downloads_folder': 'Abrir pasta de downloads',
        'clear_downloads': 'Limpar lista de downloads',
        'downloads_settings': 'Configurações de download...',
        'history_settings': 'Configurações de histórico...',
        'ai_online': 'ONLINE',
        'ai_no_key': 'SEM CHAVE',
        'ai_thinking': 'PENSANDO...',
        'key_btn': 'CHAVE',
        'summarize_page': 'RESUMIR PÁGINA',
        'clear_chat': 'LIMPAR',
        'run_btn': 'ENVIAR',
        'ai_input_placeholder': 'Perguntar ao Zephyrium AI, @page <pergunta>...',
        'ai_init_msg': 'Assistente IA Zephyrium inicializado. Inferência Gemini ativa.',
        'ai_chat_tab': 'CHAT IA',
        'scratchpad_tab': 'NOTAS',
        'adblock_settings_tab': 'Configurações do AdBlock e lista de permissões...',
        'no_downloads': 'Nenhum download ainda',
        'no_history': 'Nenhum histórico ainda',
        'container_default': 'Padrão',
        'container_work': 'Trabalho',
        'container_personal': 'Pessoal',
        'container_dev': 'Desenvolvimento',
        'container_incognito': 'Anônimo',
    },
    'it': {
        'history_title': 'CRONOLOGIA',
        'open_full_history': 'Apri cronologia completa (zephyrium://history)',
        'clear_history': 'Cancella cronologia',
        'open_all_downloads': 'Tutti i download (zephyrium://downloads)',
        'open_downloads_folder': 'Apri cartella download',
        'clear_downloads': 'Cancella elenco download',
        'downloads_settings': 'Impostazioni download...',
        'history_settings': 'Impostazioni cronologia...',
        'ai_online': 'ONLINE',
        'ai_no_key': 'SENZA CHIAVE',
        'ai_thinking': 'IN ELABORAZIONE...',
        'key_btn': 'CHIAVE',
        'summarize_page': 'RIASSUMI PAGINA',
        'clear_chat': 'CANCELLA',
        'run_btn': 'INVIA',
        'ai_input_placeholder': 'Chiedi a Zephyrium AI, @page <domanda>...',
        'ai_init_msg': 'Assistente IA Zephyrium inizializzato. Inferenza Gemini attiva.',
        'ai_chat_tab': 'CHAT IA',
        'scratchpad_tab': 'NOTE',
        'adblock_settings_tab': 'Impostazioni AdBlock e whitelist...',
        'no_downloads': 'Nessun download presente',
        'no_history': 'Nessuna cronologia presente',
        'container_default': 'Predefinito',
        'container_work': 'Lavoro',
        'container_personal': 'Personale',
        'container_dev': 'Sviluppo',
        'container_incognito': 'Anonimo',
    },
    'tr': {
        'history_title': 'GEÇMİŞ',
        'open_full_history': 'Tüm geçmişi aç (zephyrium://history)',
        'clear_history': 'Geçmişi temizle',
        'open_all_downloads': 'Tüm indirilenler (zephyrium://downloads)',
        'open_downloads_folder': 'İndirilenler klasörünü aç',
        'clear_downloads': 'İndirilenler listesini temizle',
        'downloads_settings': 'İndirme ayarları...',
        'history_settings': 'Geçmiş ayarları...',
        'ai_online': 'ÇEVRİMİÇİ',
        'ai_no_key': 'ANAHTAR YOK',
        'ai_thinking': 'DÜŞÜNÜYOR...',
        'key_btn': 'ANAHTAR',
        'summarize_page': 'SAYFAYI ÖZETLE',
        'clear_chat': 'TEMİZLE',
        'run_btn': 'GÖNDER',
        'ai_input_placeholder': "Zephyrium AI'a sor, @page <soru>...",
        'ai_init_msg': 'Zephyrium AI Asistanı başlatıldı. Canlı Gemini çıkarımı aktif.',
        'ai_chat_tab': 'AI SOHBET',
        'scratchpad_tab': 'NOTLAR',
        'adblock_settings_tab': 'AdBlock ayarları ve beyaz liste...',
        'no_downloads': 'Henüz indirme yok',
        'no_history': 'Henüz geçmiş yok',
    }
}

for lang, keys in EXTRA_TRANSLATIONS.items():
    if lang in TRANSLATIONS:
        TRANSLATIONS[lang].update(keys)

_current_language = "ru"

def get_system_default_language() -> str:
    try:
        loc, _ = locale.getdefaultlocale()
        if loc:
            prefix = loc.split("_")[0].lower()
            if prefix in LANGUAGES:
                return prefix
    except Exception:
        pass
    return "ru"

def set_language(lang_code: str) -> None:
    global _current_language
    if lang_code in LANGUAGES:
        _current_language = lang_code

def get_current_language() -> str:
    return _current_language

def t(key: str, **kwargs) -> str:
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS["en"])
    val = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
