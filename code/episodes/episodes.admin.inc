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
    '#type'        => 'radios',
    '#title'       => t('Status'),
    '#description' => t(
      'You can either disable or enable Episodes, or put it in debug mode, in
      which case it will only be applied for users with the
      %administer-site-configuration permission and logging will be disabled.',
      array('%administer-site-configuration' => t('administer site configuration'))
    ),
    '#options'     => array(
      EPISODES_DISABLED => t('Disabled'),
      EPISODES_DEBUG    => t('Debug mode'),
      EPISODES_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_STATUS_VARIABLE, EPISODES_DEBUG),
  );

  $form['advanced'] = array(
    '#type'  => 'fieldset',
    '#title' => t('Advanced settings'),
  );
  $form['advanced'][EPISODES_BEACON_URL_VARIABLE] = array(
    '#type'          => 'textfield',
    '#title'         => t('Beacon URL'),
    '#description'   => t('The beacon URL you would like to use. Can also be a URL of a different server, potentially a web service that analyzes the logs for you.'),
    '#size'          => 60,
    '#maxlength'     => 255,
    '#default_value' => variable_get(EPISODES_BEACON_URL_VARIABLE, url('episodes/beacon')),
  );
  $form['advanced'][EPISODES_LOGGING_VARIABLE] = array(
    '#type'        => 'radios',
    '#title'       => t('Logging'),
    '#description' => t("When you've enabled logging, you should provide a valid beacon URL."),
    '#options'     => array(
      EPISODES_DISABLED => t('Disabled'),
      EPISODES_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_LOGGING_VARIABLE, EPISODES_DISABLED),
  );
  $form['advanced'][EPISODES_EXCLUDED_PATHS_VARIABLE] = array(
    '#type'        => 'textarea',
    '#title'       => t('Excluded paths'),
    '#description' => t("Enter one page per line as Drupal paths. The '*'
                         character is a wildcard. Example paths are %blog for
                         the blog page and %blog-wildcard for every personal
                         blog. %front is the front page.",
                         array(
                           '%blog'          => 'blog',
                           '%blog-wildcard' => 'blog/*',
                           '%front'         => '<front>',
                         )),
    '#cols' => 60,
    '#rows' => 5,
    '#default_value' => variable_get(EPISODES_EXCLUDED_PATHS_VARIABLE, EPISODES_EXCLUDED_PATHS_DEFAULT),
  );

  $form['ingestor'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Ingestor settings'),
    '#description' => t('Only when you are using a beacon URL that points to
                         this same server and have set up Apache properly to
                         do the logging, only then, you have to configure the
                         ingestor.<br />
                         The ingestor runs during cron.'),
  );
  $form['ingestor'][EPISODES_INGESTOR_STATUS_VARIABLE] = array(
    '#type' => 'radios',
    '#title' => t('Status'),
    '#options' => array(
      EPISODES_DISABLED => t('Disabled'),
      EPISODES_ENABLED  => t('Enabled'),
    ),
    '#default_value' => variable_get(EPISODES_INGESTOR_STATUS_VARIABLE, EPISODES_INGESTOR_STATUS_DEFAULT),
  );
  
  $form['ingestor'][EPISODES_INGESTOR_LOG_FILE_VARIABLE] = array(
    '#type'        => 'textfield',
    '#title'       => t('Log file'),
    '#description' => t('The <strong>absolute path</strong> to the log file that must be ingested.'),
    '#size'        => 40,
    '#maxlength'   => 255,
    '#default_value' => variable_get(EPISODES_INGESTOR_LOG_FILE_VARIABLE, NULL),
  );
  

  return system_settings_form($form);
}

/**
 * Form definition; behaviors settings.
 */
function episodes_admin_settings_behaviors() {
  // Determine when the last scan was and create a nice string for it.
  $last_scan = variable_get(EPISODES_LAST_SCAN_VARIABLE, EPISODES_LAST_SCAN_NEVER);
  if ($last_scan != EPISODES_LAST_SCAN_NEVER) {
    $timeago = t('!interval ago', array('!interval' => format_interval(time() - $last_scan)));
  }
  else {
    $timeago = t('never');
  }
  
  // Determine the number of currently present behaviors and over how many
  // files they are spread.
  $sql = "SELECT COUNT(name)
          FROM {episodes_behavior}
          WHERE detected = %d";
  $num_behaviors = db_result(db_query($sql, $last_scan));
  $sql = "SELECT COUNT(DISTINCT filename)
          FROM episodes_behavior
          WHERE detected = %d";
  $num_files     = db_result(db_query($sql, $last_scan));
  $sql = "SELECT COUNT(DISTINCT module)
          FROM episodes_behavior
          WHERE detected = %d";
  $num_modules   = db_result(db_query($sql, $last_scan));


  // Get all behaviors, generate the options and defaults for the select.
  $behaviors = episodes_behavior_load();
  $options = array();
  $defaults = array();
  foreach ($behaviors as $behavior) {
    $options[$behavior->name] = t('!name (!module)', array('!name' => $behavior->name, '!module' => $behavior->module));
    if ($behavior->ignored) {
      $defaults[] = $behavior->name;
    }    
  }
  
  
  $form['detected_behaviors'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Detected behaviors'),
    '#description' => t("<strong>!num-behaviors behaviors</strong> in
                        !num-modules modules, spread over !num-files files
                        were detected. If you've installed new modules or
                        themes, you may want to scan again. <em>Scanning again
                        will not reset the ignored behaviors!</em>",
                        array(
                          '!num-behaviors' => $num_behaviors,
                          '!num-files'     => $num_files,
                          '!num-modules'   => $num_modules
                        )
                      )
                      . '<br />' .
                      t('Last scanned: <strong>!time-ago</strong>.', array('!time-ago' => $timeago)),
  );
  $form['detected_behaviors']['scan'] = array(
    '#type'   => 'submit', 
    '#submit' => array('episodes_admin_settings_behaviors_scan_submit'),
    '#value'  => t('Scan'),
  );

  if ($last_scan != EPISODES_LAST_SCAN_NEVER) {
    $form['ignored'] = array(
      '#type'        => 'hierarchical_select',
      '#title'       => t('Ignored behaviors'),
      '#description' => t("Select the behaviors that you <strong>don't</strong> want to be measured!"),
      '#config'      => array(
        'module' => 'hs_flatlist',
        'params' => array(
          'options' => $options,
        ),
        'save_lineage'    => 0,
        'enforce_deepest' => 0,
        'entity_count'    => 0,
        'resizable'       => 1,
        'level_labels' => array(
          'status' => 0,
        ),
        'dropbox' => array(
          'status'   => 1,
          'title'    => t('All ignored behaviors'),
          'limit'    => 0,
          'reset_hs' => 0,
        ),
        'editability' => array(
          'status' => 0,
        ),
      ),
      '#default_value' => $defaults,
      );

    $form['save'] = array(
      '#type' => 'submit', 
      '#value' => t('Save'),
    );
  }

  return $form;
}

/**
 * Default submit callback for the behaviors settings form. 
 */
function episodes_admin_settings_behaviors_submit($form, &$form_state) {
  // Mark the behavior as ignored.
  foreach ($form_state['values']['ignored'] as $behaviorname) {
    db_query("UPDATE {episodes_behavior} SET ignored = %d WHERE name = '%s'", EPISODES_BEHAVIOR_IGNORED, $behaviorname);
  }
}

/**
 * Submit callback for the 'Scan' button on the behaviors settings form.
 */
function episodes_admin_settings_behaviors_scan_submit($form, &$form_state) {
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
  $queued_files = array();
  $files_per_module = array();

  // Get the filenames of Drupal core JS files.
  $files = file_scan_directory('misc', '.*\.js');
  foreach ($files as $file) {
    $files_per_module[] = array('core', $file);
  }

  // Get the filenames of all enabled modules and themes.
  $result = db_query("SELECT filename, name AS modulename FROM {system} WHERE status = 1");
  while ($row = db_fetch_object($result)) {
    $directory = dirname($row->filename);

    // Scan the directory and store the module-file mapping.
    $files = file_scan_directory($directory, '.*\.js');
    foreach ($files as $file) {
      // Ensure we don't scan the same file twice. Some modules (e.g. Views)
      // have multiple .module files in the same directory and that would
      // result in duplicate scans. Other modules (e.g. form_builder) have a
      // nested directory structure that results in the same file being found
      // more than one time.
      if (in_array($file->filename, $queued_files)) {
        continue;
      }
      else {
        $queued_files[] = $file->filename;
      }
      $files_per_module[] = array($row->modulename, $file);
    }
  }

  // Create an operation for each JS file that was found.
  $operations = array();
  foreach ($files_per_module as $file_and_module) {
    list($modulename, $file) = $file_and_module;
    $operations[] = array('episodes_scan_behaviors_process', array($modulename, $file));
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
 * @param $modulename
 *   A module name (or theme name).
 * @param $file
 *   A file object for a JS file.
 * @param $context
 *   @see _batch_process()
 */
function episodes_scan_behaviors_process($modulename, $file, &$context = NULL) {
  // Scan file to find Drupal.behaviors.
  $content = file_get_contents($file->filename);
  $matches = array();
  preg_match_all('/\s*Drupal\.behaviors\.([a-zA-Z]+)\s+=\s+function/', $content, $matches);
  $behaviors = $matches[1];

  // Store some result for post-processing in the finished callback.
  $context['results']['files'][$file->filename] = $file;
  foreach ($behaviors as $behavior) {
    $context['results']['mappings'][] = implode(':', array($modulename, $file->filename, $behavior));
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
    drupal_set_message(t('Scanned !num-files files and found !num-behaviors behaviors.',
      array(
        '!num-files' => count($results['files']),
        '!num-behaviors' => count($results['behaviors']),
      )
    ));

    // Store the results.
    $detected = time();
    $update_count = 0;
    $new_count = 0;
    variable_set(EPISODES_LAST_SCAN_VARIABLE, $detected);
    foreach ($results['mappings'] as $mapping) {
      list($modulename, $filename, $behaviorname) = explode(':', $mapping);

      $behavior           = new stdClass();
      $behavior->name     = $behaviorname;
      $behavior->module   = $modulename;
      $behavior->filename = $filename;
      $behavior->detected = $detected;

      // If the filename has changed, mark it as an update. If no filename was
      // set, it's a newly detected behavior. Oterwise, update the database
      // with the new 'detected' date, but don't advertise it as an update to
      // the user.
      $sql = "SELECT filename
              FROM {episodes_behavior}
              WHERE module = '%s' AND name = '%s'";
      $old_filename = db_result(db_query($sql, $modulename, $behaviorname));
      if ($old_filename !== FALSE) {
        drupal_write_record('episodes_behavior', $behavior, 'name');
        if ($old_filename != $filename) {
          $update_count++;
        }
      }
      else if ($old_filename === FALSE) {
        drupal_write_record('episodes_behavior', $behavior);
        $new_count++;
      }
    }
    drupal_set_message(t('Updated !update-count behaviors, detected !new-count new behaviors.',
      array(
        '!update-count' => $update_count,
        '!new-count' => $new_count,
      )
    ));
  }
  else {
    // An error occurred.
    // $operations contains the operations that remained unprocessed.
    $error_operation = reset($operations);
    $message = 'An error occurred while processing '. $error_operation[0];
    $message .= ' with arguments :'. print_r($error_operation[0], TRUE);
    drupal_set_message($message);
  }
}
