<?php
// $Id$

/**
 * @file
 * Settings administration UI.
 */


//----------------------------------------------------------------------------
// Form API callbacks.

/**
 * Form definition; settings.
 */
function cdn_admin_settings_form() {
  $form[CDN_STATUS_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Status'),
    '#description' => t(
      "If you don't want to use the CDN to serve files to your visitors yet,
      but you do want to see if it's working well for your site, then enable
      debug mode.<br />It will only serve files from the CDN if they have the
      %cdn-debug-mode-permission permission.",
      array('%cdn-debug-mode-permission' => 'access files on CDN when in debug mode')
    ),
    '#options' => array(
      CDN_DISABLED => t('Disabled'),
      CDN_DEBUG    => t('Debug mode'),
      CDN_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(CDN_STATUS_VARIABLE, CDN_DISABLED),
  );

  $form[CDN_MODE_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Mode'),
    '#description' => t(
      "<strong>Basic mode</strong> will simply prepend another URL to the
      complete file URL. Therefor, it only works for CDNs that support the
      Origin Pull technique.<br />
      <strong>Advanced mode</strong> uses the daemon to synchronize files and
      can be used with both Origin Pull and Push CDNs. If you've got an Origin
      Pull CDN and want to process files before they're synced to the CDN, it
      is also recommended to use this mode."
    ),
    '#options' => array(
      CDN_MODE_BASIC    => t('Basic'),
      CDN_MODE_ADVANCED => t('Advanced'),
    ),
    '#default_value' => variable_get(CDN_MODE_VARIABLE, CDN_MODE_BASIC),
  );

  $form[CDN_STATS_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Show statistics for the current page'),
    '#description' => t(
      'Shows the CDN integration statistics of the current page, to users with
      the %access-per-page-statistics permission.',
      array('%access-per-page-statistics' => 'access per-page statistics')
    ),
    '#options' => array(
      CDN_DISABLED => t('Disabled'),
      CDN_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(CDN_STATS_VARIABLE, CDN_DISABLED),
  );

  return system_settings_form($form);
}

/**
 * Form definition; basic settings.
 */
function cdn_admin_basic_settings_form() {
  $form[CDN_BASIC_URL_VARIABLE] = array(
    '#type'          => 'textfield',
    '#title'         => t('CDN URL'),
    '#description'   => t("The CDN URL prefix that should be used. Only works
                           for CDNs that support Origin Pull.<br />
                           <strong>WARNING</strong>: do not use subdirectories
                           when you're serving CSS files from the CDN. The
                           references to images and fonts from within the CSS
                           files will break because the URLs are no longer
                           valid."),
    '#size'          => 35,
    '#default_value' => variable_get(CDN_BASIC_URL_VARIABLE, ''),
  );
  
  $form[CDN_BASIC_EXTENSIONS_VARIABLE] = array(
    '#type'          => 'textfield',
    '#title'         => t('Allowed extensions'),
    '#description'   => t('Only files with these extensions will be synced.'),
    '#default_value' => variable_get(CDN_BASIC_EXTENSIONS_VARIABLE, CDN_BASIC_EXTENSIONS_DEFAULT),
  );

  return system_settings_form($form);
}

/**
 * Form definition; advanced settings.
 */
function cdn_admin_advanced_settings_form() {
  // Immediately show the user the current status, unless the user is
  // currently editing the values in the form.
  if (!isset($_POST['form_build_id'])) {
    $synced_files_db = variable_get(CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE, FALSE);
    if ($synced_files_db !== FALSE) {
      if (file_exists($synced_files_db) && @fopen($synced_files_db, 'r')) {
        drupal_set_message(t('The synced files database was found and can be opened for reading.'));
      }
      else {
        drupal_set_message(t('The synced files database could not be opened for reading!', 'error'));
      }
    }
  }
    
  $form[CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE] = array(
    '#type'          => 'textfield',
    '#title'         => t('Synced files database'),
    '#description'   => t('Enter the full path to the daemon\'s synced files database file.'),
    '#size'          => 60,
    '#default_value' => variable_get(CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE, ''),
  );

  return system_settings_form($form);
}

/**
 * Form definition; other settings.
 */
function cdn_admin_other_settings_form() {
  $form[CDN_DRUPAL_ROOT_VARIABLE] = array(
    '#type' => 'textfield',
    '#title' => t('Drupal root directory'),
    '#description' => t(
      'In 99% of the cases the default value is sufficient and correct. In
      some advanced setups that make use of symbolic links however, it is
      possible that the Drupal root directory is incorrectly detected. In
      those cases, you should enter it here.<br />
      <strong>This setting only affects the status report, it does not affect
      the CDN integration itself in any way.</strong>'
    ),
    '#default_value' => variable_get(CDN_DRUPAL_ROOT_VARIABLE, realpath('.')),
  );

  return system_settings_form($form);
}

/**
 * Default validate callback for the settings form.
 */
function cdn_admin_settings_form_validate($form, &$form_state) {
  // Validate the synced files DB whenever advanced mode is enabled. It must
  // be configured (on the advanced settings form) *before* advanced mode can
  // be enabled!
  $enabled  = isset($form_state['values'][CDN_STATUS_VARIABLE]) && $form_state['values'][CDN_STATUS_VARIABLE] != CDN_DISABLED;
  $advanced = isset($form_state['values'][CDN_MODE_VARIABLE])   && $form_state['values'][CDN_MODE_VARIABLE]   == CDN_MODE_ADVANCED;
  if ($enabled && $advanced) {
    $synced_files_db = variable_get(CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE, '');
    if (!_validate_synced_files_db($synced_files_db, CDN_STATUS_VARIABLE)) {
      drupal_set_message(t('Please correct the above error in the <em>Advanced mode</em> settings form first.'), 'error');
    }
  }
}

/**
 * Default validate callback for the advancedsettings form.
 */
function cdn_admin_advanced_settings_form_validate($form, &$form_state) {
  // Validate the synced files DB when it's filled out on the advanced
  // settings form.
  if (isset($form_state['values'][CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE])) {
    $synced_files_db = $form_state['values'][CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE];
    _validate_synced_files_db($synced_files_db, CDN_ADVANCED_SYNCED_FILES_DB_VARIABLE);
  }
}


//----------------------------------------------------------------------------
// Private functions.

/**
 * Helper function to validate a possible synced files DB value.
 *
 * @param $synced_files_db
 *   A user-entered synced files DB value.
 * @param $name
 *   The name of the form item on which to set errors, if any.
 * @return
 *   FALSE if there were any errors, TRUE if there weren't any.
 */
function _validate_synced_files_db($synced_files_db, $name) {
  // Validate the file name.
  if (strpos($synced_files_db, CDN_DAEMON_SYNCED_FILES_DB) === FALSE) {
    form_set_error($name, t('The synced files database should have the file name %name.', array('%name' => CDN_DAEMON_SYNCED_FILES_DB)));
    return FALSE;
  }

  // Validate the entered synced files database.
  if (!file_exists($synced_files_db)) {
    form_set_error($name, t('The synced files database does not exist.'));
    return FALSE;
  }
  else {
    if (!@fopen($synced_files_db, 'r')) {
      form_set_error($name, t('The synced files database could not be opened for reading.'));
      return FALSE;
    }
  }

  return TRUE;
}
