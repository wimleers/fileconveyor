// $Id$

(function($) {

// Override Drupal.attachBehaviors with a version that does measurements at
// the appropriate times through EPISODES.
Drupal.attachBehaviors = function(context) {
  context = context || document;
  
  var count = 0;
  for (behavior in Drupal.behaviors) {
    count++;
    break;
  }

  if (Drupal.jsEnabled && count) {
    window.postMessage("EPISODES:mark:DrupalBehaviors", document.location);
    for (behavior in Drupal.behaviors) {
      window.postMessage("EPISODES:mark:" + behavior, document.location);
      Drupal.behaviors[behavior](context);
      window.postMessage("EPISODES:measure:" + behavior, document.location);
    }
    window.postMessage("EPISODES:measure:DrupalBehaviors", document.location);
  }
};
// Add a domready measurement. This event occurs before all images and other
// referenced binaries have finished loading. It uses the DOMContentLoaded
// event in browsers that support it, and an emulation of that for Internet
// Explorer.
// TODO: instead of relying on jQuery and having this event outside of the
// "core" episodes.js, include it there? Ask Steve Souders.
$(document).ready(function() {
  window.postMessage("EPISODES:measure:domready:frontendstarttime", document.location);
});

// Drupal.Episodes object. Allows Drupal modules to specify lazy load
// callbacks. Each callback should only return as soon as it's truly finished
// with lazy loading content.
// Only when all lazy load callbacks are finished, EPISODES will be notified
// that the page is completely loaded and the "totaltime" episode can be
// calculated. Only then the results will be sent to the beacon.
Drupal.Episodes = {};
Drupal.Episodes.lazyLoadReady = false;
Drupal.Episodes.lazyLoadList = [];
Drupal.Episodes.addLazyLoadCallback = function(callback) {
  // Add the callback to the lazy load callbacks list.
  Drupal.Episodes.lazyLoadList.push(callback);
};
Drupal.Episodes.executeLazyLoadCallbacks = function() {
  jQuery.each(Drupal.Episodes.lazyLoadList, function(){ this.call(); });
  Drupal.Episodes.lazyLoadReady = true;
};
Drupal.Episodes.done = function() {
  if (Drupal.Episodes.lazyLoadReady) {
    // Mark: "totaltime". We use this mark as the endmark for both the
    // lazyloading and totaltime measures because they may otherwise differ.
    window.postMessage("EPISODES:mark:totaltime", document.location);

    // Measure: "totaltime"
    // When lazy loading was performed: (totaltime - backend start time)
    // Otherwise: (pageready - backend start time).
    var endMark = (Drupal.Episodes.lazyLoadList.length > 0) ? 'totaltime' : 'pageready';
    window.postMessage("EPISODES:measure:totaltime:backendstarttime:" + endMark, document.location);
    if (Drupal.Episodes.lazyLoadList.length > 0) {
      // Measure: "lazyloading" (totaltime - pageready).
      window.postMessage("EPISODES:measure:lazyloading:pageready:totaltime", document.location);
    }
    // Done!
    window.postMessage("EPISODES:done", document.location);
  }
  else {
    setTimeout(arguments.callee, 0);
    return;
  }
};


// Call Drupal.Episodes.done() when the "load" event is triggered.
EPISODES.addEventListener("load", function() { Drupal.Episodes.done(); }, false);

// Start executing lazy load callbacks as soon as the DOM is ready.
$(document).ready(function() { Drupal.Episodes.executeLazyLoadCallbacks(); });


$(document).ready(function() {
  setTimeout('EPISODES.rtt();', 100);
});

EPISODES.rtt = function() {
  var before = Number(new Date());
  $.get('http://dev/d6/episodes/rtt-estimator', null, function(before) {
    var after = Number(new Date());
    console.log(after - before);
  });
};


})(jQuery);
