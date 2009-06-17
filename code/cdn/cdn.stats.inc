<?php
// $Id$

/**
 * @file
 * Per-page CDN integration statistics functionality.
 */


//----------------------------------------------------------------------------
// Private functions.

/**
 * Collects per-page CDN integration statistics.
 *
 * @param $file
 *   The local file path.
 * @param $file_cdn_url
 *   The URL to the file on the CDN if it exists, FALSE otherwise.
 * @param $server
 *   The server the file exists on.
 * @param $time
 *   The time it took to get the current CDN URL.
 * @return
 *   Only if no parameters were passed: the collected statistics.
 */
function _cdn_devel_page_stats($file = FALSE, $file_cdn_url = FALSE, $server = FALSE, $time = FALSE) {
  static $file_count;
  static $cdn_file_count;
  static $synced_files_per_server_count;
  static $total_time;
  static $synced_files;
  static $unsynced_files;
  static $drupal_root_path;

  if (!isset($drupal_root_path)) {
    $drupal_root_path = dirname('.');
  }

  if (!isset($file_count)) {
    $file_count = 0;
    $cdn_file_count = 0;
    $synced_files_per_server_count = array();
    $total_time = 0;
    $synced_files = array();
    $unsynced_files = array();
  }

  // If the function is called with parameters set, save the statistics. If no
  // parameters are passed, return the collected statistics.
  if ($file) {
    $file_count++;
    $total_time += $time;

    if ($file_cdn_url !== FALSE) {
      $cdn_file_count++;

      $synced_files[] = array(
        'file'          => $file,
        'absolute path' => realpath($drupal_root_path . '/' . $file),
        'cdn_url'       => $file_cdn_url,
        'server'        => ($server === FALSE) ? '' : $server,
      );

      // $server is only set in advanced mode.
      if ($server !== FALSE) {
        if (!array_key_exists($server, $synced_files_per_server_count)) {
          $synced_files_per_server_count[$server] = 0;
        }
        $synced_files_per_server_count[$server]++;
      }
    }
    else {
      $unsynced_files[] = $file;
    }
  }
  elseif (!$file) {
    return array(
      $file_count,
      $cdn_file_count,
      $synced_files_per_server_count,
      $total_time,
      $synced_files,
      $unsynced_files,
    );
  }
}
