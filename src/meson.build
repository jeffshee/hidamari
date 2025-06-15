pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'src'
appdatadir = get_option('prefix') / get_option('datadir') / 'data'

gnome = import('gnome')

gnome.compile_resources('hidamari',
  'hidamari.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)
conf.set('moduledir', moduledir)
conf.set('appdatadir', appdatadir)

configure_file(
  input: 'hidamari.in',
  output: 'hidamari',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

build_config_file = configure_file(
  input: 'config/build_config.py.in',
  output: 'build_config.py',
  configuration: conf,
  install: false,
)

hidamari_sources = [
  'main.py',
  'actions/app_actions.py',
  'config/app_config.py',
  'config/paths_config.py',
  'config/preferences_config.py',
  'config/shortcuts_config.py',
  'config/stores_config.py',
  'config/ui_config.py',
  'messages/messages.py',
  'stores/freshclam_config_store.py',
  'stores/logbook_store.py',
  'stores/preferences_store.py',
  'utils/clamav.py',
  'utils/i18n.py',
  'utils/process.py',
  'utils/ui_helpers.py',
  'widgets/base/base_list_view.py',
  'widgets/base/base_status_page.py',
  'widgets/base/conditional_stack.py',
  'widgets/base/preferences_window.py',
  'widgets/base/progress_page.py',
  'widgets/dialogues/about_dialog.py',
  'widgets/dialogues/logbook_entry_dialog.py',
  'widgets/dialogues/shortcuts_dialog.py',
  'widgets/logbook/logbook.py',
  'widgets/radar/radar.py',
  'widgets/radar/scan_result_page.py',
  'widgets/radar/scan_target_selector.py',
  'widgets/update/update.py',
  'widgets/window.py'
]

install_data(hidamari_sources, install_dir: moduledir, preserve_path: true)

install_data(build_config_file, install_dir: moduledir / 'config')