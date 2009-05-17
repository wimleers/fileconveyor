<?php
// $Id$

/**
 * Render the CDN integration page statistics.
 *
 * @param $file_count
 *   The number of files detected on this page.
 * @param $cdn_file_count
 *   The number of files on this page that are served from a CDN.
 * @param $synced_files_per_server_count
 *   The number of files synced to each server.
 * @param $synced_files
 *   Array of synchronized files.
 * @param $unsynced_files
 *   Array of unsynchronized files.
 * @return
 *   The rendered HTML.
 */
function theme_cdn_page_stats($file_count, $cdn_file_count, $synced_files_per_server_count, $synced_files, $unsynced_files) {
  $output = '';
  $items = array();
  $mode = variable_get(CDN_MODE_VARIABLE, CDN_MODE_BASIC);

  $output .= '<div id="cdn-integration-page-stats">';
  $items[] = 'Total number of files on this page: <strong>'. $file_count .'</strong>.';
  $percentage = ($file_count == 0) ? '100' : number_format($cdn_file_count / $file_count * 100);
  $items[] = 'Number of files available on CDNs: <strong>'. $cdn_file_count .'</strong> ('. $percentage . '% coverage).';
  if ($mode == CDN_MODE_ADVANCED) {
    foreach (array_keys($synced_files_per_server_count) as $server) {
      $items[] = t('Number of files served from the server %server: !count', array('%server' => $server, '!count' => $synced_files_per_server_count[$server]));
    }
  }
  else {
    $items[] = 'All files are being served from a single CDN, because basic mode is being used.';
  }
  
  
  // Nested list of unsynced files.
  if (count($unsynced_files)) {
    $unsynced_items = array();
    foreach ($unsynced_files as $file) {
      $unsynced_items[] = array(l($file, $file));
    }
    $items[] = 'The files that are not (yet?) synchronized to the CDN:' . theme('item_list', $unsynced_items, NULL, 'ol');
  }

  // Nested list of synced files.
  if (count($synced_files)) {
    $synced_items = array();
    foreach (array_keys($synced_files) as $file) {
      $cdn_url = $synced_files[$file]['cdn_url'];
      $server  = $synced_files[$file]['server'];
      $text = ($mode == CDN_MODE_BASIC) ? '!file' : '!file (server: !server)';
      $synced_items[] = array(l(t($text, array('!file' => $file, '!server' => $server)), $cdn_url));
    }
    $items[] = 'The files that are synchronized to the CDN:' . theme('item_list', $synced_items, NULL, 'ol');
  }

  $output .= theme('item_list', $items, '<strong>'. t('CDN integration statistics for %drupal_path', array('%drupal_path' => $_GET['q'])) .'</strong>');
  $output .= '</div>';
  return $output;
}
