<?php
// $Id$

/**
 * @file
 * Reports UI.
 */


/**
 * Menu callback; reports UI; overall.
 */
function episodes_server_report_overall() {
  $output = '';

  drupal_set_title('Episodes analysis - overall');

  $num_episodes           = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode}"));
  $num_frontend_episodes  = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'frontend'"));
  $num_backend_episodes   = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'backend'"));
  $num_countries          = db_result(db_query("SELECT COUNT(DISTINCT(country)) FROM {episodes_server_episode}"));
  $since_date             = db_result(db_query("SELECT MIN(server_time) FROM {episodes_server_episode}"));
  $until_date             = db_result(db_query("SELECT MAX(server_time) FROM {episodes_server_episode}"));

  $output .= '<p>' . t('<strong>!num-episodes episode measurements</strong>
                        have been collected over !num-frontend-episodes
                        page views (!num-backend-episodes of which also
                        contain measurements of the back-end) <strong>from
                        !since-date to !until-date</strong>, with visitors
                        coming from !num-countries countries.',
                        array(
                          '!num-episodes'           => $num_episodes,
                          '!num-frontend-episodes'  => $num_frontend_episodes,
                          '!num-backend-episodes'   => $num_backend_episodes,
                          '!since-date'             => format_date($since_date, 'large'),
                          '!until-date'             => format_date($until_date, 'large'),
                          '!num-countries'          => $num_countries,
                        )
                     ) . '</p>';
  $output .= '<br /><br />';

  return $output;
}


function episodes_server_report_filter_form($form_state) {
  // Build list of countries.
  $countries = array();
  $result = db_query("SELECT DISTINCT(country) AS country FROM {episodes_server_episode}");
  while ($row = db_fetch_object($result)) {
    // Deal with countries ip2country didn't know.
    if ($row->country == '') {
      $row->country = 'unknown';
    }
    $country_info = countries_api_get_country($row->country);
    $country_name = ($country_info !== FALSE && $country_info !== NULL) ? $country_info['printable_name'] : $row->country;
    $countries[$row->country] = $country_name;
  }
  $countries[''] = '<none>';
  asort($countries);

  $form['filters'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Filters'),
    '#collapsible' => FALSE,
    '#weight'      => -1,
  );
  $form['filters']['countries'] = array(
    '#type'          => 'hierarchical_select',
    '#title'         => t('Comparison countries'),
    '#description'   => t('Compare other countries with the global statistics.'),
    '#config'      => array(
      'module' => 'hs_flatlist',
      'params' => array(
        'options' => $countries,
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
        'title'    => t('Selected countries'),
        'limit'    => 0,
        'reset_hs' => 0,
      ),
      'editability' => array(
        'status' => 0,
      ),
    ),
    '#default_value' => (isset($form_state['values']['countries'])) ? $form_state['values']['countries'] : array(),
  );

  $form['filters']['apply'] = array(
    '#type' => 'submit', 
    '#value' => t('Apply'),
  );

  $form['#submit'][] = '_episodes_server_report_shared_submit';

  return $form;
}

function _episodes_server_report_shared_submit($form, &$form_state) {
  $form_state['rebuild'] = TRUE;
}

function _episodes_server_report_plp_details($country, $country_code) {
  static $weight;

  if (!isset($weight)) {
    $weight = 0;
  }
  else {
    $weight++;
  }

  $grid_step_percentage = 10;

  $backends = $frontends = $num_pageloads = array();

  // backend episodes.
  $sql = "SELECT CONCAT(YEAR(FROM_UNIXTIME(server_time)), ' ', MONTH(FROM_UNIXTIME(server_time)), ' ', DAY(FROM_UNIXTIME(server_time))) AS day,
                 AVG(duration) AS avg
          FROM {episodes_server_episode}
          WHERE name = 'backend'";
  if (isset($country_code)) {
    $sql .= " AND country = '%s'";
  }
  $sql .= " GROUP BY day";
  $result = db_query($sql, $country_code);
  while ($row = db_fetch_object($result)) {
    $backends[$row->day] = $row->avg;
  }

  // frontend episodes and number of  pageloads.
  $sql = "SELECT CONCAT(YEAR(FROM_UNIXTIME(server_time)), ' ', MONTH(FROM_UNIXTIME(server_time)), ' ', DAY(FROM_UNIXTIME(server_time))) AS day,
                 AVG(duration) AS avg,
                 COUNT(duration) AS count
          FROM {episodes_server_episode}
          WHERE name = 'frontend'";
  if (isset($country_code)) {
    $sql .= " AND country = '%s'";
  }
  $sql .= " GROUP BY day";
  $result = db_query($sql, $country_code);
  while ($row = db_fetch_object($result)) {
    $frontends[$row->day]     = $row->avg;
    $num_pageloads[$row->day] = $row->count;
  }

  // Build basic form structure which we'll use to group content together.
  $form['chart' . $country] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Chart (!country)', array('!country' => $country)),
    '#collapsible' => TRUE,
    '#weight'      => $weight,
  );
  $form['chart' . $country]['output'] = array(
    '#value'  => NULL, // Will be set after the chart has been rendered.
    '#prefix' => '<div>',
    '#suffix' => '</div>',
  );
  $form['table' . $country] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Table (!country)', array('!country' => $country)),
    '#collapsible' => TRUE,
    '#weight'      => 1,
    '#weight'      => $weight + 10000,
  );
  $form['table' . $country]['output'] = array(
    '#value'  => NULL, // Will be set after the table has been rendered.
    '#prefix' => '<div>',
    '#suffix' => '</div>',
  );

  // Render chart.
  $chart = array();
  $chart['#chart_id'] = 'chart-page-loading-performance-' . $country;
  $chart['#type'] = CHART_TYPE_LINE;
  $chart['#size']['#width'] = 700;
  $chart['#size']['#height'] = 200;
  $chart['#data'] = array();
  $chart['#legends'][] = 'backend';
  $chart['#legends'][] = 'frontend';
  $chart['#adjust_resolution'] = TRUE;
  $chart['#grid_lines'] = chart_grid_lines($grid_step_percentage, 0); // Grid lines every 10% of the chart.
  $chart['#data_colors'] = array(
    'FF4117',
    '3D6BFF',
    '298F3C',
  );
  $j = 0;
  foreach (array_keys($backends) as $date) {
    $backend   = $backends[$date];
    $frontend  = $frontends[$date];

    $chart['#data']['backend'][]   = $backend;
    $chart['#data']['frontend'][]  = $frontend;
  }
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(reset(array_keys($backends)), 0);
  $center = ceil(count($backends) / 2);
  $keys = array_keys($backends);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label($keys[$center], 50);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(end(array_keys($backends)), 100);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][1][] = chart_mixed_axis_label(t('Date'), 95);
  $max_avg = ceil(max($chart['#data']['frontend']) / 10) * 10;
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][0][] = chart_mixed_axis_range_label(0, $max_avg, $max_avg / 100 * 20);
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][1][] = chart_mixed_axis_label(t("Duration (ms)"), 95);
  $output_chart .= chart_render($chart);
  $form['chart' . $country]['output']['#value'] = $output_chart;

  // Render table.
  $header = array(t('Date'), t('Page loads'), 'backend', 'frontend');
  $rows = array();
  foreach (array_keys($backends) as $date) {
    $backend   = $backends[$date];
    $frontend  = $frontends[$date];
    $pageloads = $num_pageloads[$date];
    
    $rows[] = array($date, $pageloads, $backend, $frontend);
  }
  $form['table' . $country]['output']['#value'] = theme('table', $header, $rows);

  return array($form, $frontends);
}

function _episodes_server_report_plp_frontend_comparison_chart($frontends_per_country) {
  $grid_step_percentage = 10;
  $chart = array();
  $chart['#chart_id'] = 'chart-page-loading-performance-comparison';
  $chart['#type'] = CHART_TYPE_LINE;
  $chart['#size']['#width'] = 700;
  $chart['#size']['#height'] = 200;
  $chart['#data'] = array();
  foreach (array_keys($frontends_per_country) as $country_code) {
    $country_info = countries_api_get_country($country_code);
    $country_name = ($country_info !== FALSE && $country_info !== NULL) ? $country_info['printable_name'] : $country_code;
    $chart['#legends'][] = $country_name;
  }
  $chart['#adjust_resolution'] = TRUE;
  $chart['#grid_lines'] = chart_grid_lines($grid_step_percentage, 0); // Grid lines every 10% of the chart.
  $chart['#data_colors'] = array(
    'FF4117',
    '3D6BFF',
    '298F3C',
    'FF66F2'
  );
  $j = 0;
  $max = 0;
  foreach (array_keys($frontends_per_country) as $country_code) {
    foreach (array_keys($frontends_per_country[$country_code]) as $date) {
      $frontend = $frontends_per_country[$country_code][$date];
      $chart['#data'][$country_code][] = $frontend;
      $max = max($max, $frontend);
    }
  }
  $frontends_of_first_country = $frontends_per_country[reset(array_keys($frontends_per_country))];
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(reset(array_keys($frontends_of_first_country)), 0);
  $center = ceil(count($frontends_of_first_country) / 2);
  $keys = array_keys($frontends_of_first_country);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label($keys[$center], 50);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(end(array_keys($frontends_of_first_country)), 100);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][1][] = chart_mixed_axis_label(t('Date'), 95);
  $max_avg = ceil($max / 10) * 10;
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][0][] = chart_mixed_axis_range_label(0, $max_avg, $max_avg / 100 * 20);
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][1][] = chart_mixed_axis_label(t("Duration (ms)"), 95);
  return chart_render($chart);
}

function episodes_server_report_plp($form_state) {
  $output = '';

  drupal_set_title('Episodes analysis - page loading performance');

  // Filters.
  $form = episodes_server_report_filter_form($form_state);
  if (array_key_exists('values', $form_state)) {
    if ($form_state['values']['countries'] != 0) {
      $filter_countries = $form_state['values']['countries'];
    }
  }

  // Page loading performance.
  $comparison_frontends = array();
  list($subform, $frontends) = _episodes_server_report_plp_details('global');
  $comparison_frontends['global'] = $frontends;
  $form = array_merge($form, $subform);
  if (isset($filter_countries)) {
    foreach ($filter_countries as $country_code) {
      $country_info = countries_api_get_country($country_code);
      $country_name = ($country_info !== FALSE && $country_info !== NULL) ? $country_info['printable_name'] : $country_code;
      list($subform, $frontends) = _episodes_server_report_plp_details($country_name, $country_code);

      // Merge the subform with the main form.
      $form = array_merge($form, $subform);

      // Store the received frontend episodes for this country.
      $comparison_frontends[$country_code] = $frontends;
    }

    $form['comparisonchart'] = array(
      '#type'        => 'fieldset',
      '#title'       => t('Comparison of frontend episodes'),
      '#collapsible' => TRUE,
      '#weight'      => count($filter_countries) + 10,
    );
    $form['comparisonchart']['output'] = array(
      '#value'  => NULL, // Will be set after the chart has been rendered.
      '#prefix' => '<div>',
      '#suffix' => '</div>',
    );
    $form['comparisonchart']['output']['#value'] = _episodes_server_report_plp_frontend_comparison_chart($comparison_frontends);
  }

  return $form;
}


/**
 * Menu callback; reports UI; episodes.
 */
function episodes_server_report_episodes() {
  $output = '';

  drupal_set_title('Episodes analysis - episodes');

  $lower_boundary = 10;
  $grid_step_percentage = 10;

  $ignored_episodes = array('totaltime', 'backend', 'pageready');
  $container_episodes = array_merge($ignored_episodes, array('frontend', 'domready', 'DrupalBehaviors'));


  //--------------------------------------------------------------------------
  // Filters.
  
/*
  $form['#method'] = 'GET';
  $form['filters'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Filters'),
    '#collapsible' => FALSE,
  );
  $form['filters']['reset'] = array(
    '#type'  => 'submit', 
    '#value' => t('Reset all filters'),
  );
  $output .= drupal_render($form);
*/

  //--------------------------------------------------------------------------
  // Episodes.

  // Query the database.
  $avgs = $stds = $labels = array();
  $result = db_query("SELECT name,
                             AVG(duration) AS avg,
                             STD(duration) AS std
                      FROM {episodes_server_episode}
                      GROUP BY name
                      HAVING avg > %d
                      ORDER BY avg DESC
                      ", $lower_boundary);
  while ($row = db_fetch_object($result)) {
    $labels[] = $row->name;
    $avgs[] = (float) $row->avg;
    $stds[] = (float) $row->std;
  }

  // Build basic form structure which we'll use to group content together.
  $form = array();
  $form['chart'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Chart'),
    '#collapsible' => TRUE,
  );
  $form['chart']['output'] = array(
    '#value'  => NULL, // Will be set after the chart has been rendered.
    '#prefix' => '<div>',
    '#suffix' => '</div>',
  );
  $form['table'] = array(
    '#type'        => 'fieldset',
    '#title'       => t('Table'),
    '#collapsible' => TRUE,
    '#collapsed'   => !isset($_GET['sort']), // If the user is sorting the table, display it immediately.
    '#weight'      => 1,
  );
  $form['table']['output'] = array(
    '#value'  => NULL, // Will be set after the table has been rendered.
    '#prefix' => '<div>',
    '#suffix' => '</div>',
  );

  // Chart information.
  $output_chart = '<p>' . t('Not displayed in this chart') . ':';
  $items = array(
    t('episodes that need less than !lower-boundary ms', array('!lower-boundary' => $lower_boundary)),
    t('episodes that contain other episodes'),
  );
  $output_chart .= theme('item_list', $items);
  $output_chart .= '</p>';

  // Render chart.
  $chart = array();
  $chart['#chart_id'] = 'chart-episodes';
  $chart['#type'] = CHART_TYPE_BAR_H;
  $chart['#size']['#width'] = 500;
  $chart['#data'] = array();
  $chart['#adjust_resolution'] = TRUE;
  $chart['#grid_lines'] = chart_grid_lines($grid_step_percentage, 0, 0, 0); // Grid lines every 10% of the chart.
  $chart['#data_colors'][0] = 'C6D9FD';
  $j = 0;
  for ($i = 0; $i < count($avgs); $i++) {    
    $avg = $avgs[$i];
    $label = $labels[$i];
    $episode_type = (in_array($label, $container_episodes)) ? 'container-episode' : 'episode';

    // Some episodes should always be ignored, but others only when they are
    // too insignificant. Displayin *all* data on a chart doesn't work well.
    if (in_array($label, $ignored_episodes) || $avg < $lower_boundary)
      continue;

    $chart['#data'][] = $avg;
    //$chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][0][] = chart_mixed_axis_label($label, 100 - $j * 8);
    $chart['#shape_markers'][] = array(
      '#type'  => "t $label",
      '#color' => '000000',
      '#index' => 0,
      '#point' => $j,
      '#size'  => 13,
    );
    $j++;
  }

//  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][1][] = chart_mixed_axis_label(t('Duration (ms)'), 95);
  $chart['#size']['#height'] = 30 + count($chart['#data']) * 30;
  $max_avg = ceil(max($chart['#data']) / 10) * 10;
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_range_label(0, $max_avg, $max_avg / 100 * $grid_step_percentage);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][1][] = chart_mixed_axis_label(t('Duration (ms)'), 95);
  $output_chart .= chart_render($chart);
  $form['chart']['output']['#value'] = $output_chart;


  // Construct the header of the table.
  $header = array(
    array('data' => t('Episode'),            'field' => 'name', 'sort' => NULL),
    array('data' => t('Average duration'),   'field' => 'avg',  'sort' => 'desc'),
    array('data' => t('Standard deviation'), 'field' => 'std',  'sort' => NULL),
    t('Type'),
  );

  // Query the database.
  $avgs = $stds = $labels = array();
  $sql = "SELECT name,
                 AVG(duration) AS avg,
                 STD(duration) AS std
          FROM {episodes_server_episode}
          GROUP BY name";
  $sql .= tablesort_sql($header);
  $result = db_query($sql);
  while ($row = db_fetch_object($result)) {
    $labels[] = $row->name;
    $avgs[] = (float) $row->avg;
    $stds[] = (float) $row->std;
  }

  // Render table.
  $rows = array();
  for ($i = 0; $i < count($avgs); $i++) {
    $avg          = $avgs[$i];
    $std          = $stds[$i];
    $label        = $labels[$i];
    $type         = (in_array($label, $container_episodes)) ? 'container' : 'episode';
    $label        = ($type == 'container') ? '<strong>' . $label . '</strong>' : $label;
    $episode_type = ($type == 'container') ? t('Container') : t('Episode');
    
    $rows[] = array($label, $avg, $std, $episode_type);
  }
  $form['table']['output']['#value'] = theme('table', $header, $rows);

  // Render the form structure, which contains both the chart and the table.
  $output .= drupal_render($form);

  return $output;
}
