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
function episodes_admin_settings() {
  $form[EPISODES_STATUS_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Status'),
    '#description' => t(
      'You can either disable or enable Episodes, or put it in debug mode, in
      which case it will only be applied for users with the
      %administe-site-configuration permission',
      array('%administer-site-configuration' => t('administer site configuration'))
    ),
    '#options' => array(
      EPISODES_STATUS_DISABLED => t('Disabled'),
      EPISODES_STATUS_DEBUG    => t('Debug mode'),
      EPISODES_STATUS_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_STATUS_VARIABLE, EPISODES_STATUS_DEBUG),
  );

  $form[EPISODES_LOGGING_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Logging'),
    '#description' => t("When you've enabled logging, you should provide"),
    '#options' => array(
      EPISODES_LOGGING_DISABLED => t('Disabled'),
      EPISODES_LOGGING_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_LOGGING_VARIABLE, EPISODES_LOGGING_DISABLED),
  );

  $form['save'] = array(
    '#type' => 'submit', 
    '#value' => t('Save'),
  );

  return $form;
}

/**
 * Form definition; settings for behaviors.
 */
function episodes_admin_settings_behaviors() {
  $form['detected_behaviors'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Detected behaviors'),
    '#description' => t("<strong>!num-behaviors behaviors</strong> in
                        !num-files files were detected. If you've installed
                        new modules or themes, you way want to scan again.",
                        array('!num-behaviors' => '', '!num-files' => '')
                      )
                      . '<br />' .
                      t('Last scanned: <strong>!time-ago</strong>.', array('!time-ago' => '')),
  );
  $form['detected_behaviors']['scan'] = array(
    '#type'   => 'submit', 
    '#submit' => array('episodes_admin_settings_behaviors_scan_submit'),
    '#value'  => t('Scan'),
  );
  
  $form['save'] = array(
    '#type' => 'submit', 
    '#value' => t('Save'),
  );

  return $form;
}

function episodes_admin_settings_behaviors_scan_submit() {
  drupal_goto('admin/settings/episodes/behaviors/scan');
}


//----------------------------------------------------------------------------
// Menu system callbacks.

/**
 * Page callback; initializes the batch process.
 */
function episodes_scan_behaviors() {
  batch_set(episodes_scan_behaviors_batch());

  // Trigger batch processing.
  batch_process('admin/settings/episodes/behaviors');

  return '';
}


//----------------------------------------------------------------------------
// Batch API callbacks.

/**
 * Batch definition callback; generate all operations for the batch process.
 */
function episodes_scan_behaviors_batch() {
  $files = array();

  // Get the filenames of Drupal core JS files.
  $files += file_scan_directory('misc', '.*\.js');

  // Get the filenames of all enabled modules and themes.
  $result = db_query("SELECT filename FROM {system} WHERE status = 1");
  while ($row = db_fetch_object($result)) {
    $directory = dirname($row->filename);
    $files += file_scan_directory($directory, '.*\.js');
  }

  // Create an operation for each JS file that was found.
  $operations = array();
  foreach ($files as $file) {
    $operations[] = array('episodes_scan_behaviors_process', array($file));
  }

  $batch = array(
    'title'            => t('Scanning Drupal installation for Drupal.behaviors'),
    'file'             => drupal_get_path('module', 'episodes') . '/episodes.admin.inc',
    'operations'       => $operations,
    'finished'         => 'episodes_scan_behaviors_results',
    'init_message'     => t('Scan process is starting.'),
    'progress_message' => t('Scanned @current files out of @total files (@percentage%). @remaining remaining.'),
    'error_message'    => t('Scan process has encountered an error.'),
  );

  return $batch;
}

/**
 * Batch process callback; process a JS file and scan it to find behaviors.
 *
 * @param $file
 *   A file object for a JS file.
 * @param $context
 *   @see _batch_process()
 */
function episodes_scan_behaviors_process($file, &$context = NULL) {
  // Scan file to find Drupal.behaviors.
  $content = file_get_contents($file->filename);
  $matches = array();
  preg_match_all('/\s*Drupal\.behaviors\.([a-zA-Z]+)\s+=\s+function/', $content, $matches);
  $behaviors = $matches[1];

  // Store some result for post-processing in the finished callback.
  $context['results']['files'][] = $file;
  foreach ($behaviors as $behavior) {
    $context['results']['behaviormappings'][] = $file->filename . ':' . $behavior;
    $context['results']['behaviors'][] = $behavior;
  }

  // Optional message displayed under the progressbar.
  $context['message'] = 'Scanned '. $file->filename;
}

/**
 * Batch finished callback; display some messsages and store the results.
 *
 * @param $success
 *   @see _batch_finished()
 * @param $results
 *   @see _batch_finished()
 * @param $operations
 *   @see _batch_finished()
 */
function episodes_scan_behaviors_results($success, $results, $operations) {
  if ($success) {
    // Generate message.
    $message = t('Scanned !num-files files and found !num-behaviors behaviors:',
      array(
        '!num-files' => count($results['files']),
        '!num-behaviors' => count($results['behaviors']),
      )
    );
    $message .= theme('item_list', $results['behaviors']);

    // Store the results.
    // TODO!!!
    dpm('the results are not yet stored…');
  }
  else {
    // An error occurred.
    // $operations contains the operations that remained unprocessed.
    $error_operation = reset($operations);
    $message = 'An error occurred while processing '. $error_operation[0] .' with arguments :'. print_r($error_operation[0], TRUE);
  }
  drupal_set_message($message);
}
