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
  $num_totaltime_episodes = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'totaltime'"));
  $num_backend_episodes   = db_result(db_query("SELECT COUNT(eid) FROM {episodes_server_episode} WHERE name = 'backend'"));
  $since_date             = db_result(db_query("SELECT MIN(server_time) FROM {episodes_server_episode}"));

  $output .= '<p>' . t('<strong>!num-episodes episode measurements</strong>
                        have been collected over !num-totaltime-episodes
                        page views (!num-backend-episodes of which also
                        contain measurements of the back-end) <strong>since
                        !since-date.</strong>',
                        array(
                          '!num-episodes'           => $num_episodes,
                          '!num-totaltime-episodes' => $num_totaltime_episodes,
                          '!num-backend-episodes'   => $num_backend_episodes,
                          '!since-date'             => format_date($since_date, 'large'),
                        )
                     ) . '</p>';


  //--------------------------------------------------------------------------
  // Page loading performance.

  $output .= '<h2>' . t('Page loading performance') . '</h2>';

  $totaltimes = $backends = $frontends = array();
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
                             AVG(duration) AS avg
                      FROM {episodes_server_episode}
                      WHERE name = 'frontend'
                      GROUP BY day");
  while ($row = db_fetch_object($result)) {
    $frontends[$row->day] = $row->avg;
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
  $header = array(t('Date'), 'totaltime', 'backend', 'frontend');
  $rows = array();
  foreach (array_keys($totaltimes) as $date) {
    $totaltime = $totaltimes[$date];
    $backend   = $backends[$date];
    $frontend  = $frontends[$date];
    
    $rows[] = array($date, $totaltime, $backend, $frontend);
  }
  $form['table']['output']['#value'] = theme('table', $header, $rows);

  // Render the form structure, which contains both the chart and the table.
  $output .= drupal_render($form);


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

  $chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][] = chart_mixed_axis_label(array(t('Count')), 95);
  $chart['#size']['#height'] = count($chart['#data']) * 30;
  $max_avg = ceil(max($chart['#data']) / 10) * 10;
  $chart['#mixed_axis_labels'][CHART_AXIS_X_BOTTOM][0][] = chart_mixed_axis_range_label(0, $max_avg, $max_avg / 100 * $grid_step_percentage);
  rsort($chart['#mixed_axis_labels'][CHART_AXIS_Y_LEFT][0]);
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

/*
  // generate some random data
  srand((double)microtime()*1000000);


  $data = array();
  for( $i=0; $i<6; $i++ )
  {
    $data[] = rand(5,9);
  }

  $g = new open_flash_chart_api('');
  $g->set_title( 'Bar Chart', '{font-size: 20px;}' );
  $g->set_width(200);

  //
  // BAR CHART:
  //
  $g->set_data( $data );
  $g->bar( 50, '#9933CC', '#8010A0', 'Page views', 10 );
  //
  // ------------------------
  //

  //
  // X axis tweeks:
  //
  $g->set_x_labels( array( 'January' ,'February', 'March', 'April', 'May', 'June' ) );
  //
  // set the X axis to show every 2nd label:
  //
  $g->set_x_label_style( 10, '#9933CC', 0, 2 );
  //
  // and tick every second value:
  //
  $g->set_x_axis_steps( 2 );
  //

  $g->set_y_max( 10 );
  $g->y_label_steps( 4 );
  $g->set_y_legend( 'Open Flash Chart', 12, '#736AFF' );
  $g->set_bg_colour('0xDFFFDF');
  return $g->render();
*/
  


/*
// generate some random data
srand((double)microtime()*1000000);

$data_1 = array();
$data_2 = array();
for( $i=0; $i<2; $i++ )
{
  // rand gives us an integer, so devide it
  // by 10 to give us a float number between
  // 5 and 9
  $data_1[] = rand(50,90)/10;
  $data_2[] = rand(-50,-90)/10;
}

$g = new open_flash_chart_api();
$g->title( 'min=-10 max=10', '{font-size: 35px; color: #800000}' );

$g->set_data( $data_1 );
$g->bar( 50, '#800000', 'Rusty', 10 );

$g->set_data( $data_2 );
$g->bar_filled( 50, '#9933CC', '#8010A0', 'Purple Nurple', 10 );

$g->set_x_labels( array( 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep' ) );

$g->set_y_min( -9.5 );
$g->set_y_max( 10.5 );

$g->y_label_steps( 5 );
$g->set_y_legend( 'Your legend here!', 12, '#736AFF' );
$g->set_width(500);
$g->set_height(200);

return $g->render();


*/



/*



$a = array();
$b = array();
$labels = array();

$a[] = new candle(10,10,4,4);
$b[] = new candle(10,8,6,4);
$labels[] = 'Mon';
$a[] = new candle(20,15,10,5);
$b[] = new candle(20,10,15,5);
$labels[] = 'Tue';
$a[] = new candle(20,15,10,5);
$b[] = new candle(28,24,18,16);
$labels[] = 'Wed';
$a[] = new candle(20,10,15,5);
$b[] = new candle(10,6,9,4);
$labels[] = 'Thu';
$a[] = new candle(30,5,27,2);
$b[] = new candle(5,4,2,1);
$labels[] = 'Fri';

//
// ----
//
$g = new open_flash_chart_api();
$g->title( 'candle', '{font-size: 26px;}' );

//$g->set_data( $data );

//
// LOOK:
//
$g->candle( $a, 60, 2, '#C11B01', 'My Company', 12 );
$g->candle( $b, 60, 2, '#B0C101', 'Your Company', 12 );
//
//
$g->set_tool_tip( '#x_legend#<br>High: #high#<br>Open: #open#<br>Close: #close#<br>Low: #low#' );
//
//

$g->set_x_labels( $labels );
$g->set_x_label_style( 10, '#000000', 0, 1 );
$g->set_x_legend( 'Week 1', 12, '#C11B01' );

$g->set_y_min( 0 );
$g->set_y_max( 30 );

$g->y_label_steps( 10 );
$g->set_y_legend( 'Value', 12, '#C11B01' );
$g->set_width(500);
$g->set_height(200);

return $g->render();
*/

/*
$example = array(
    '#plugin'    => 'google', // Google Charts API will be used
    '#height'   => 100, // in pixels
    '#width'    => 200, // in pixels
    
  '#type'     => 'pie3D', // Display a 3D pie chart
  '#color'    => 'f0f0f0', // Background color, in RRGGBB format
  '#title'    => t('Example'), // Chart title
  array(
    array('#value' => 60, '#label' => t('60%')),
    array('#value' => 25, '#label' => t('25%')),
    array('#value' => 10, '#label' => t('10%')),
    array('#value' => 5,  '#label' => t('5%')),
  ),
);
return charts_chart($example);
*/

  
  
  
  
  $element = array(
    'id' => 'chart-no-1',
    'style' => 'width: 300px;height:150px',
  );
  $d1 = new flotData(array(array(0, 1), array(4, 8), array(8, 5)));
  $d2 = new flotData(array(array(0, 8), array(3, 5), array(8, 0.5)));
  $output .=  theme('flot_graph', $element, array($d1, $d2));

  // Episodes
  $element = array(
    'id'    => 'chart-episodes',
    'style' => 'width:100%;height:200px',
  );
  $min = array();
  $max = array();
  $avg = array();
  $labels = array();
  $result = db_query("SELECT name,
                             MIN(duration) AS min,
                             MAX(duration) AS max,
                             AVG(duration) AS avg
                      FROM {episodes_server_episode}
                      GROUP BY name");
  $id = 0;
  while ($row = db_fetch_object($result)) {
    if ($row->avg < 10 || $row->avg > 100)
      continue;
    $labels[] = array($id, $row->name);
    $min[] = array($id, (float) $row->min);
    $max[] = array($id, (float) $row->max);
    $avg[] = array($id, (float) $row->avg);
    $id++;
  }

//array(0, 1), array(1, 1), array(2, 3)
dpm($labels);
  $serie = new flotData($avg);
//    $serie->label = 'average';
  $serie->bars = array('show' => TRUE, 'barWidth' => 0.5);
  $data[] = $serie;

/*
  $serie = new flotData(array(array(0, 1.5), array(1, 1.2), array(2, 3.1)));
//    $serie->label = 'max';
  $serie->color = 'red';
  $serie->points = array('show' => TRUE);
  $data[] = $serie;

  $serie = new flotData(array(array(0, 0.8), array(1, 0.4), array(2, 2.5)));
//    $serie->label = 'min';
  $serie->color = 'blue';
  $serie->points = array('show' => TRUE);
  $data[] = $serie;
*/

  $output .= theme('flot_graph', $element, $data, array('xaxis' => array('ticks' => $labels)));

  return $output;
}


// Display average page load time per continent, zoom, avg page load time
// per country, zoom, per city
