<?php
// $Id$

/**
 * @file
 * Functions used to ingest the log files.
 */


/**
 * Given an entry (a line) from the log file, write a measurement to the
 * database if it's relevant.
 * A measurement is relevant if if has a 200 HTTP response code
 *
 * @param $entry
 *   An entry from the log file.
 * @return
 *   All measured episodes when the entry was valid, FALSE otherwise.
 */
function episodes_ingestor_parse_entry($entry) {
  static $browser;
  $matches = array();
  $measurements = array();

  require_once drupal_get_path('module', 'episodes') . '/lib/Browser.php';

  if (!isset($browser)) {
    $browser = new Browser();
  }

  // If the entry is invalid, then we ignore it altogether.
  if (!preg_match('/^(\S+) \[(.*)\] "(.*)" (\S+) "(.*)" "(.*)" "(.*)"/', $entry, $matches)) {
    return FALSE;
  }
  else {
    // Ignore log entries that resulted in any other HTTP response than 200.
    if ($matches[4] != 200) {
      return FALSE;
    }

    // Collect all data we can get without a lot of processing. Immediately
    // ensure the data fits the constraints within which it will be stored.
    $measurement = new stdClass();
    $measurement->client_ip   = $matches[1];
    $measurement->server_time = strtotime($matches[2]);
    $measurement->uri         = substr($matches[5], 0, 255);
    $measurement->user_agent  = substr($matches[6], 0, 255);
    $measurement->server_host = substr($matches[7], 0, 255);

    // Get the browser details.
    $browser->setUserAgent($measurement->user_agent);
    $measurement->browser         = substr($browser->getBrowser(), 0, 32);
    $measurement->browser_version = substr($browser->getVersion(), 0, 8);
    $measurement->os              = substr($browser->getPlatform(), 0, 32);

    // Get the parameters of the query string.
    $parameters = array();
    // Explanation of the regular expression:
    //  ^[^?]*    # throw away path info before first ?
    //  \?        # must have a ? or there's no query string
    //  (.*)$     # capture everything to end
    preg_match('/^[^?]*\?(.*)$/', $matches[3], $matches);
    // foo=123&bar=456
    $querystring = $matches[1];
    // array('foo', 123, 'bar', 456)
    $parts = explode('=', $querystring);
    // array('foo' => 123, 'bar' => 456)
    for ($i = 0; $i < count($parts); $i += 2) {
      $parameters[$parts[$i]] = $parts[$i + 1];
    }

    // Get all measured episodes along with their durations.
    $episodes = explode(',', $parameters['ets']);
    foreach ($episodes as $episode) {
      list($name, $duration) = explode(':', $episode);
      $measurement->name     = $name;
      $measurement->duration = $duration;
      $measurements[] = drupal_clone($measurement);

      // Finally, write the measurement object to the database!
      drupal_write_record('episodes_measurement', $measurement);
    }
  }

  return $measurements;
}
