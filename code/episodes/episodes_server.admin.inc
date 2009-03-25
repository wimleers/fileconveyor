<?php
// $Id$

/**
 * @file
 * Settings administration UI.
 */


//----------------------------------------------------------------------------
// Forms API callbacks.

/**
 * Form definition; settings.
 */
function episodes_server_admin_settings() {
  $form['ingestor'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Ingestor settings'),
    '#description' => t('Only when you are using a beacon URL that points to
                         this same server and have set up Apache properly to
                         do the logging, only then, you have to configure the
                         ingestor.<br />
                         The ingestor runs during cron.'),
  );
  $form['ingestor'][EPISODES_SERVER_INGESTOR_STATUS_VARIABLE] = array(
    '#type'    => 'radios',
    '#title'   => t('Status'),
    '#options' => array(
      EPISODES_SERVER_DISABLED => t('Disabled'),
      EPISODES_SERVER_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_SERVER_INGESTOR_STATUS_VARIABLE, EPISODES_SERVER_INGESTOR_STATUS_DEFAULT),
  );
  
  $form['ingestor'][EPISODES_SERVER_INGESTOR_LOG_FILE_VARIABLE] = array(
    '#type'          => 'textfield',
    '#title'         => t('Log file'),
    '#description'   => t('The <strong>absolute path</strong> to the log file that must be ingested.'),
    '#size'          => 40,
    '#maxlength'     => 255,
    '#default_value' => variable_get(EPISODES_SERVER_INGESTOR_LOG_FILE_VARIABLE, NULL),
  );

  return system_settings_form($form);
}
