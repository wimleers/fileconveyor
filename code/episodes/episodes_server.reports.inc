<?php
// $Id$

/**
 * @file
 * Reports UI.
 */


/**
 * Menu callback; reports UI.
 */
function episodes_server_report() {
  $output = '';

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
  // Overall statistics.

  $num_episodes           = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode}"));
  $num_frontend_episodes  = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'frontend'"));
  $num_backend_episodes   = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'backend'"));
  $since_date             = db_result(db_query("SELECT MIN(server_time) FROM {episodes_server_episode}"));

  $output .= '<p>' . t('<strong>!num-episodes episode measurements</strong>
                        have been collected over !num-frontend-episodes
                        page views (!num-backend-episodes of which also
                        contain measurements of the back-end) <strong>since
                        !since-date.</strong>',
                        array(
                          '!num-episodes'           => $num_episodes,
                          '!num-frontend-episodes' => $num_frontend_episodes,
                          '!num-backend-episodes'   => $num_backend_episodes,
                          '!since-date'             => format_date($since_date, 'large'),
                        )
                     ) . '</p>';
  $output .= '<br /><br />';


  //--------------------------------------------------------------------------
  // Page loading performance.

  $output .= '<h2>' . t('Page loading performance') . '</h2>';

  $totaltimes = $backends = $frontends = $num_pageloads = array();
  $result = db_query("SELECT CONCAT(YEAR(FROM_UNIXTIME(server_time)), ' ', MONTH(FROM_UNIXTIME(server_time)), ' ', DAY(FROM_UNIXTIME(server_time))) AS day,
                             AVG(duration) AS avg
                      FROM {episodes_server_episode}
                      WHERE name = 'totaltime'
                      GROUP BY day");
  while ($row = db_fetch_object($result)) {
    $totaltimes[$row->day] = $row->avg;
  }
  $result = db_query("SELECT CONCAT(YEAR(FROM_UNIXTIME(server_time)), ' ', MONTH(FROM_UNIXTIME(server_time)), ' ', DAY(FROM_UNIXTIME(server_time))) AS day,
                             AVG(duration) AS avg
                      FROM {episodes_server_episode}
                      WHERE name = 'backend'
                      GROUP BY day");
  while ($row = db_fetch_object($result)) {
    $backends[$row->day] = $row->avg;
  }
  $result = db_query("SELECT CONCAT(YEAR(FROM_UNIXTIME(server_time)), ' ', MONTH(FROM_UNIXTIME(server_time)), ' ', DAY(FROM_UNIXTIME(server_time))) AS day,
                             AVG(duration) AS avg,
                             COUNT(duration) AS count
                      FROM {episodes_server_episode}
                      WHERE name = 'frontend'
                      GROUP BY day");
  while ($row = db_fetch_object($result)) {
    $frontends[$row->day]     = $row->avg;
    $num_pageloads[$row->day] = $row->count;
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

  // Render chart.
  $chart = array();
  $chart['#chart_id'] = 'chart-page-loading-performance';
  $chart['#type'] = CHART_TYPE_LINE;
  $chart['#size']['#width'] = 800;
  $chart['#size']['#height'] = 200;
  $chart['#data'] = array();
  $chart['#legends'][] = 'totaltime';
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
  foreach (array_keys($totaltimes) as $date) {
    $totaltime = $totaltimes[$date];
    $backend   = $backends[$date];
    $frontend  = $frontends[$date];

    $chart['#data']['totaltime'][] = $totaltime;
    $chart['#data']['backend'][]   = $backend;
    $chart['#data']['frontend'][]  = $frontend;
  }
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(reset(array_keys($totaltimes)), 0);
  $center = ceil(count($totaltimes) / 2);
  $keys = array_keys($totaltimes);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label($keys[$center], 50);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_label(end(array_keys($totaltimes)), 100);
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][1][] = chart_mixed_axis_label(t('Date'), 95);
  $max_avg = ceil(max($chart['#data']['totaltime']) / 10) * 10;
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][0][] = chart_mixed_axis_range_label(0, $max_avg, $max_avg / 100 * 20);
  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][1][] = chart_mixed_axis_label(t("Duration (ms)"), 95);
  $output_chart .= chart_render($chart);
  $form['chart']['output']['#value'] = $output_chart;

  // Render table.
  $header = array(t('Date'), t('Page loads'), 'totaltime', 'backend', 'frontend');
  $rows = array();
  foreach (array_keys($totaltimes) as $date) {
    $totaltime = $totaltimes[$date];
    $backend   = $backends[$date];
    $frontend  = $frontends[$date];
    $pageloads = $num_pageloads[$date];
    
    $rows[] = array($date, $pageloads, $totaltime, $backend, $frontend);
  }
  $form['table']['output']['#value'] = theme('table', $header, $rows);

  // Render the form structure, which contains both the chart and the table.
  $output .= drupal_render($form);
  $output .= '<br /><br />';

  //--------------------------------------------------------------------------
  // Episodes.

  $output .= '<h2>' . t('Episodes') . '</h2>';

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
  $chart['#grid_lines'] = chart_grid_lines($grid_step_percentage, 0); // Grid lines every 10% of the chart.
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
