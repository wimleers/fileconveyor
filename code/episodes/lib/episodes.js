//////////////////////////////////////////////////////////////////////////////////
//                                                                               //
// This is the episode management code. It gathers all the episodic timing       //
// information, returns that as a data structure, and can send it as a beacon    //
// to a specified URL.                                                           //
//                                                                               //
// This code could come from one of three places:                                //
//   1. implemented by the owner of the web page                                 //
//   2. from the implementation of "episodes.js" shared across the industry      //
//   3. in the future, this functionality would be built into the browser itself //
//                                                                               //
///////////////////////////////////////////////////////////////////////////////////


// Don't overwrite pre-existing instances of the object (esp. for older browsers).
var EPISODES = EPISODES || {};

EPISODES.init = function() {
	EPISODES.done = false;
    EPISODES.marks = {};
    EPISODES.measures = {};
    EPISODES.starts = {};
	EPISODES.addEventListener("message", EPISODES.handleEpisodeMessage, false);
	EPISODES.findStartTime();
	window.postMessage("EPISODES:mark:backendstarttime:" + EPISODES.backendStartTime, document.location);
	window.postMessage("EPISODES:mark:frontendstarttime:" + EPISODES.frontendStartTime, document.location);
	window.postMessage("EPISODES:measure:backend:backendstarttime:frontendstarttime", document.location);
	EPISODES.addEventListener("beforeunload", EPISODES.beforeUnload, false);
	EPISODES.addEventListener("load", function() {
	// Mark: "pageready". We use this mark as the endmark for both the
	// pageready and frontend measures because they may otherwise differ.
	window.postMessage("EPISODES:mark:pageready", document.location);
	// Measure: "pageready" (page ready - backend start time).
	window.postMessage("EPISODES:measure:pageready:backendstarttime:pageready", document.location);
	// Measure: "frontend" (page ready - front end start time or first byte)
	window.postMessage("EPISODES:measure:frontend:frontendstarttime:pageready", document.location);
	}, false);
};

EPISODES.isCompatible = function() {
	return ( "undefined" != typeof(window.postMessage) );
};

// Load the compatibility module if necessary. 
// Do this AFTER we define EPISODES.init to avoid race conditions.
if ( ! EPISODES.isCompatible() ) {
	if ( -1 === window.navigator.userAgent.indexOf("MSIE") ) {
		// NOT IE
		var se = document.createElement('script');
		se.src = EPISODES.compatScriptUrl;
		document.getElementsByTagName('head')[0].appendChild(se); 
	}
	else {
		// IE
		document.write('<scr' + 'ipt src="' + EPISODES.compatScriptUrl + '"></scr' + 'ipt>');
	}
};

// Parse an EPISODES message and perform the desired function.
EPISODES.handleEpisodeMessage = function(event) {
    var message = event.data;
    var aParts = message.split(':');
    if ( "EPISODES" === aParts[0] ) {
		var action = aParts[1];
		if ( "init" === action ) {
			// "EPISODES:init"
			EPISODES.init();
		}
		else if ( "mark" === action ) {
			// "EPISODES:mark:markName[:markTime]"
			var markName = aParts[2];
			EPISODES.marks[markName] = aParts[3] || Number(new Date());
		}
		else if ( "measure" === action ) {
			// "EPISODES:measure:episodeName[:startMarkName|startEpochTime[:endMarkName|endEpochTime]]"
			var episodeName = aParts[2];

			// If no startMarkName is specified, assume it's the same as the episode name.
			var startMarkName = ( "undefined" != typeof(aParts[3]) ? aParts[3] : episodeName );
      // If the startMarkName doesn't exist, assume it's an actual time measurement.
			var startEpochTime = ( "undefined" != typeof(EPISODES.marks[startMarkName]) ? EPISODES.marks[startMarkName] : 
								   ( ("" + startMarkName) === parseInt(startMarkName) ? startMarkName : undefined ) );

			var endEpochTime = ( "undefined" === typeof(aParts[4]) ? Number(new Date()) : 
								 ( "undefined" != typeof(EPISODES.marks[aParts[4]]) ? EPISODES.marks[aParts[4]] : aParts[4] ) );

            if ( startEpochTime ) {
			    EPISODES.measures[episodeName] = parseInt(endEpochTime - startEpochTime);
			    EPISODES.starts[episodeName] = parseInt(startEpochTime);
            }
		}
		else if ( "done" === action ) {
			// "EPISODES:done"
			EPISODES.done = true;
    		EPISODES.sendBeacon(EPISODES.beaconUrl);
    	}
    }
};

// Return an object of episode names and their corresponding durations.
EPISODES.getMeasures = function() {
	return EPISODES.measures;
};

// Return an object of episode names and their corresponding durations.
EPISODES.getStarts = function() {
	return EPISODES.starts;
};

// Construct a querystring of episodic time measurements and send it to the specified URL.
EPISODES.sendBeacon = function(url) {
	var measures = EPISODES.getMeasures();
	var sTimes = "";
	for ( var key in measures ) {
		sTimes += "," + key + ":" + measures[key];
	}

	if ( sTimes ) {
		// strip the leading ","
		sTimes = sTimes.substring(1);

		url += "?ets=" + sTimes;

		// Send the beacon.
		var connection = (window.XMLHttpRequest)  ? new XMLHttpRequest() : (window.ActiveXObject)  ? new ActiveXObject("Microsoft.XMLHTTP") : null;
		connection.open('GET', url, true);
		connection.send(null);
	}

    return "";
};

// Use various techniques to determine the time at which this page started.
EPISODES.findStartTime = function() {
	var aCookies = document.cookie.split(' ');
	for ( var i = 0; i < aCookies.length; i++ ) {
		if ( 0 === aCookies[i].indexOf("EPISODES=") ) {
			var aSubCookies = aCookies[i].substring("EPISODES=".length).split('&');
			var startTime, bReferrerMatch;
			for ( var j = 0; j < aSubCookies.length; j++ ) {
				if ( 0 === aSubCookies[j].indexOf("s=") ) {
					startTime = aSubCookies[j].substring(2);
				}
				else if ( 0 === aSubCookies[j].indexOf("r=") ) {
					var startPage = aSubCookies[j].substring(2, aSubCookies[j].length - 1);
					bReferrerMatch = ( escape(document.referrer) == startPage );
				}
			}
			if ( bReferrerMatch && startTime ) {
				window.postMessage("EPISODES:mark:backendstarttime:" + startTime, document.location);
			}
		}
	}
};

// Set a cookie when the page unloads. Consume this cookie on the next page to get a "start time".
EPISODES.beforeUnload = function(e) {
	document.cookie = "EPISODES=s=" + Number(new Date()) + "&r=" + escape(document.location) + "; path=/";
};

// Wrapper for FF's window.addEventListener and IE's window.attachEvent.
EPISODES.addEventListener = function(sType, callback, bCapture) {
	if ( "undefined" != typeof(window.attachEvent) ) {
		return window.attachEvent("on" + sType, callback);
	}
	else if ( window.addEventListener ){
		return window.addEventListener(sType, callback, bCapture);
	}
};

if ( EPISODES.isCompatible() ) {
	// If this browser is NOT compatible, we call EPISODES.init at the bottom of episodes-compat.js.
	EPISODES.init();
};
