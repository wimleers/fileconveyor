<?php
	/**
	 * File: Browser.php
	 * Author: Chris Schuld (http://chrisschuld.com/)
	 * Last Modified: March 14, 2009
	 * @version 1.3
	 * @package PegasusPHP
	 * 
	 * Copyright (C) 2008-2009 Chris Schuld  (chris@chrisschuld.com)
	 *
	 * This program is free software; you can redistribute it and/or
	 * modify it under the terms of the GNU General Public License as
	 * published by the Free Software Foundation; either version 2 of
	 * the License, or (at your option) any later version.
	 *
	 * This program is distributed in the hope that it will be useful,
	 * but WITHOUT ANY WARRANTY; without even the implied warranty of
	 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	 * GNU General Public License for more details at:
	 * http://www.gnu.org/copyleft/gpl.html
	 *
	 *
	 * Typical Usage:
	 * 
	 *   $browser = new Browser();
	 *   if( $browser->getBrowser() == Browser::BROWSER_FIREFOX && $browser->getVersion() >= 2 ) {
	 *   	echo 'You have FireFox version 2 or greater';
	 *   }
	 *
	 * User Agents Sampled from: http://www.useragentstring.com/
	 * 
	 * This implementation is based on the original work from Gary White
	 * http://apptools.com/phptools/browser/
	 * 
	 * Gary White noted: "Since browser detection is so unreliable, I am
	 * no longer maintaining this script. You are free to use and or
	 * modify/update it as you want, however the author assumes no
	 * responsibility for the accuracy of the detected values."
	 * 
	 * Anyone experienced with Gary's script might be interested in these notes:
	 * 
	 *   Added class constants
	 *   Added detection and version detection for Google's Chrome
	 *   Updated the version detection for Amaya
	 *   Updated the version detection for Firefox
	 *   Updated the version detection for Lynx
	 *   Updated the version detection for WebTV
	 *   Updated the version detection for NetPositive
	 *   Updated the version detection for IE
	 *   Updated the version detection for OmniWeb
	 *   Updated the version detection for iCab
	 *   Updated the version detection for Safari
	 *   Updated Safari to remove mobile devices (iPhone)
	 *   Added detection for iPhone
	 *   Removed Netscape checks (matches heavily with firefox & mozilla)
	 * 
	 * 
	 * ADDITIONAL UPDATES:
	 * 
	 * 2008-11-07:
	 *  + Added Google's Chrome to the detection list
	 *  + Added isBrowser(string) to the list of functions special thanks to
	 *    Daniel 'mavrick' Lang for the function concept (http://mavrick.id.au)
	 * 
	 * 2008-12-09:
	 *  + Removed unused constant
	 *
	 * 2009-02-16: (Rick Hale)
	 *  + Added version detection for Android phones.
	 * 
	 * 2009-03-14:
	 *  + Added detection for iPods.
	 *  + Added Platform detection for iPhones
	 *  + Added Platform detection for iPods
	 * 
	 */

	class Browser {
		private $_agent = '';
		private $_browser_name = '';
		private $_version = '';
		private $_platform = '';
		private $_os = '';
		private $_is_aol = false;
		private $_aol_version = '';

		const BROWSER_UNKNOWN = 'unknown';
		const VERSION_UNKNOWN = 'unknown';
		
		const BROWSER_OPERA = 'Opera';
		const BROWSER_WEBTV = 'WebTV';
		const BROWSER_NETPOSITIVE = 'NetPositive';
		const BROWSER_IE = 'Internet Explorer';
		const BROWSER_POCKET_IE = 'Pocket Internet Explorer';
		const BROWSER_GALEON = 'Galeon';
		const BROWSER_KONQUEROR = 'Konqueror';
		const BROWSER_ICAB = 'iCab';
		const BROWSER_OMNIWEB = 'OmniWeb';
		const BROWSER_PHOENIX = 'Phoenix';
		const BROWSER_FIREBIRD = 'Firebird';
		const BROWSER_FIREFOX = 'Firefox';
		const BROWSER_MOZILLA = 'Mozilla';
		const BROWSER_AMAYA = 'Amaya';
		const BROWSER_LYNX = 'Lynx';
		const BROWSER_SAFARI = 'Safari';
		const BROWSER_IPHONE = 'iPhone';
        const BROWSER_IPOD = 'iPod';
		const BROWSER_CHROME = 'Chrome';
        const BROWSER_ANDROID = 'Android';
        
		const PLATFORM_UNKNOWN = 'unknown';
		const PLATFORM_WINDOWS = 'Windows';
		const PLATFORM_WINDOWS_CE = 'Windows CE';
		const PLATFORM_APPLE = 'Apple';
		const PLATFORM_LINUX = 'Linux';
		const PLATFORM_OS2 = 'OS/2';
		const PLATFORM_BEOS = 'BeOS';
		const PLATFORM_IPHONE = 'iPhone';
		const PLATFORM_IPOD = 'iPod';
		
		const OPERATING_SYSTEM_UNKNOWN = 'unknown';
		
		public function __construct() {
			$this->reset();
			$this->determine();
		}
		/**
		 * Reset all properties
		 */
		public function reset() {
			$this->_agent = $_SERVER['HTTP_USER_AGENT'];
			$this->_browser_name = self::BROWSER_UNKNOWN;
			$this->_version = self::VERSION_UNKNOWN;
			$this->_platform = self::PLATFORM_UNKNOWN;
			$this->_os = self::OPERATING_SYSTEM_UNKNOWN;
			$this->_is_aol = false;
			$this->_aol_version = self::VERSION_UNKNOWN;
		}
		
		/**
		 * Check to see if the specific browser is valid
		 * @param string $browserName
		 * @return True if the browser is the specified browser
		 */
		function isBrowser($browserName) { return( 0 == strcasecmp($this->_browser_name, trim($browserName))); }

		/**
		 * The name of the browser.  All return types are from the class contants
		 * @return string Name of the browser
		 */
		public function getBrowser() { return $this->_browser_name; }
		/**
		 * Set the name of the browser
		 * @param $browser The name of the Browser
		 */
		public function setBrowser($browser) { return $this->_browser_name = $browser; }
		/**
		 * The name of the platform.  All return types are from the class contants
		 * @return string Name of the browser
		 */
		public function getPlatform() { return $this->_platform; }
		/**
		 * Set the name of the platform
		 * @param $platform The name of the Platform
		 */
		public function setPlatform($platform) { return $this->_platform = $platform; }
		/**
		 * The version of the browser.
		 * @return string Version of the browser (will only contain alpha-numeric characters and a period)
		 */
		public function getVersion() { return $this->_version; }
		/**
		 * Set the version of the browser
		 * @param $version The version of the Browser
		 */
		public function setVersion($version) { $this->_version = ereg_replace('[^0-9,.,a-z,A-Z]','',$version); }
		/**
		 * The version of AOL.
		 * @return string Version of AOL (will only contain alpha-numeric characters and a period)
		 */
		public function getAolVersion() { return $this->_aol_version; }
		/**
		 * Set the version of AOL
		 * @param $version The version of AOL
		 */
		public function setAolVersion($version) { $this->_aol_version = ereg_replace('[^0-9,.,a-z,A-Z]','',$version); }
		/**
		 * Is the browser from AOL?
		 * @return boolean True if the browser is from AOL otherwise false
		 */
		public function isAol() { return $this->_is_aol; }
		/**
		 * Set the browser to be from AOL
		 * @param $isAol
		 */
		public function setAol($isAol) { $this->_is_aol = $isAol; }
		/**
		 * Get the user agent value in use to determine the browser
		 * @return string The user agent from the HTTP header
		 */
		public function getUserAgent() { return $this->_agent; }
		/**
		 * Set the user agent value (the construction will use the HTTP header value - this will overwrite it)
		 * @param $agent_string The value for the User Agent
		 */
		public function setUserAgent($agent_string) {
			$this->reset();
			$this->_agent = $agent_string;
			$this->determine();
		}
		/**
		 * Protected routine to calculate and determine what the browser is in use (including platform)
		 */
		protected function determine() {
			$this->checkPlatform();
			$this->checkBrowsers();
			$this->checkForAol();
		}

		/**
		 * Protected routine to determine the browser type
		 * @return boolean True if the browser was detected otherwise false
		 */
		protected function checkBrowsers() {
			return (
						$this->checkBrowserInternetExplorer() ||
						$this->checkBrowserFirefox() ||
						$this->checkBrowserChrome() ||
                        $this->checkBrowserAndroid() ||
						$this->checkBrowserSafari() ||
						$this->checkBrowserOpera() ||
						$this->checkBrowserNetPositive() ||
						$this->checkBrowserFirebird() ||
						$this->checkBrowserGaleon() ||
						$this->checkBrowserKonqueror() ||
						$this->checkBrowserIcab() ||
						$this->checkBrowserOmniWeb() ||
						$this->checkBrowserPhoenix() ||
						$this->checkBrowserWebTv() ||
						$this->checkBrowserAmaya() ||
						$this->checkBrowserLynx() ||
						$this->checkBrowseriPhone() ||
						$this->checkBrowseriPod() ||
						$this->checkBrowserMozilla() /* Mozilla is such an open standard that you must check it last */	
						);
		}

		/**
		 * Determine if the user is using an AOL User Agent
		 * @return boolean True if the browser is from AOL otherwise false
		 */
		protected function checkForAol() {
			$retval = false;
			if( eregi("AOL", $this->_agent) ) {
				$aversion = explode(' ',stristr($this->_agent, "AOL"));
				$this->setAol(true);
				$this->setAolVersion(ereg_replace("[^0-9,.,a-z,A-Z]", "", $aversion[1]));
				$retval = true;
			}
			else {
				$this->setAol(false);
				$this->setAolVersion(self::VERSION_UNKNOWN);
				$retval = true;
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is Internet Explorer or not
		 * @return boolean True if the browser is Internet Explorer otherwise false
		 */
		protected function checkBrowserInternetExplorer() {
			$retval = false;

			// Test for v1 - v1.5 IE
			if( eregi('microsoft internet explorer', $this->_agent) ) {
				$this->setBrowser(self::BROWSER_IE);
				$this->setVersion('1.0');
				$aresult = stristr($this->_agent, '/');
				if( egeg('308|425|426|474|0b1', $var) ) {
					$this->setVersion('1.5');
				}
				$retval = true;
			}
			// Test for versions > 1.5
			else if( eregi('msie',$this->_agent) && !eregi('opera',$this->_agent) ) {
				$aresult = explode(' ',stristr(str_replace(';','; ',$this->_agent),'msie'));
				$this->setBrowser( self::BROWSER_IE );
				$this->setVersion($aresult[1]);
				$retval = true;
			}
			// Test for Pocket IE
			else if( eregi('mspie',$this->_agent) || eregi('pocket', $this->_agent) ) {
				$aresult = explode(' ',stristr($this->_agent,'mspie'));
				$this->setPlatform( self::PLATFORM_WINDOWS_CE );
				$this->setBrowser( self::BROWSER_POCKET_IE );
				
				if( eregi('mspie', $this->_agent) ) {
					$this->setVersion($aresult[1]);
				}
				else {
					$aversion = explode('/',$this->_agent);
					$this->setVersion($aversion[1]);
				}
				$retval = true;
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is Opera or not
		 * @return boolean True if the browser is Opera otherwise false
		 */
		protected function checkBrowserOpera() {
			$retval = false;
			if( eregi('opera',$this->_agent) ) {
				$resultant = stristr($this->_agent, 'opera');
				if( eregi('/',$resultant) ) {
					$aresult = explode('/',$resultant);
					$aversion = explode(' ',$aresult[1]); 
					$this->setVersion($aversion[0]);
					$this->_browser_name = self::BROWSER_OPERA;
					$retval = true;
				}
				else {
					$aversion = explode(' ',stristr($resultant,'opera'));
					$this->setVersion($aversion[1]);
					$this->_browser_name = self::BROWSER_OPERA;
					$retval = true;
				}
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is WebTv or not
		 * @return boolean True if the browser is WebTv otherwise false
		 */
		protected function checkBrowserWebTv() {
			$retval = false;
			if( eregi('webtv',$this->_agent) ) {
				$aresult = explode("/",stristr($this->_agent,"webtv"));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->_browser_name = self::BROWSER_WEBTV;
				$retval = true;
			}
			return $retval;
		}
				
		/**
		 * Determine if the browser is NetPositive or not
		 * @return boolean True if the browser is NetPositive otherwise false
		 */
		protected function checkBrowserNetPositive() {
			$retval = false;
			if( eregi('NetPositive',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'NetPositive'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->_browser_name = self::BROWSER_NETPOSITIVE;
				$this->_platform = self::PLATFORM_BEOS;
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is Galeon or not
		 * @return boolean True if the browser is Galeon otherwise false
		 */
		protected function checkBrowserGaleon() {
			$retval = false;
			if( eregi('galeon',$this->_agent) ) {
				$aresult = explode(' ',stristr($this->_agent,'galeon'));
				$aversion = explode('/',$aresult[0]);
				$this->setVersion($aversion[1]);
				$this->setBrowser(self::BROWSER_GALEON);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is Konqueror or not
		 * @return boolean True if the browser is Konqueror otherwise false
		 */
		protected function checkBrowserKonqueror() {
			$retval = false;
			if( eregi('Konqueror',$this->_agent) ) {
				$aresult = explode(' ',stristr($this->_agent,'Konqueror'));
				$aversion = explode('/',$aresult[0]);
				$this->setVersion($aversion[1]);
				$this->setBrowser(self::BROWSER_KONQUEROR);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is iCab or not
		 * @return boolean True if the browser is iCab otherwise false
		 */
		protected function checkBrowserIcab() {
			$retval = false;
			if( eregi('icab',$this->_agent) ) {
				$aversion = explode(' ',stristr(str_replace('/',' ',$this->_agent),'icab'));
				$this->setVersion($aversion[1]);
				$this->setBrowser(self::BROWSER_ICAB);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is OmniWeb or not
		 * @return boolean True if the browser is OmniWeb otherwise false
		 */
		protected function checkBrowserOmniWeb() {
			$retval = false;
			if( eregi('omniweb',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'omniweb'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_OMNIWEB);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is Phoenix or not
		 * @return boolean True if the browser is Phoenix otherwise false
		 */
		protected function checkBrowserPhoenix() {
			$retval = false;
			if( eregi('Phoenix',$this->_agent) ) {
				$aversion = explode('/',stristr($this->_agent,'Phoenix'));
				$this->setVersion($aversion[1]);
				$this->setBrowser(self::BROWSER_PHOENIX);
				$retval = true;
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is Firebird or not
		 * @return boolean True if the browser is Firebird otherwise false
		 */
		protected function checkBrowserFirebird() {
			$retval = false;
			if( eregi('Firebird',$this->_agent) ) {
				$aversion = explode('/',stristr($this->_agent,'Firebird'));
				$this->setVersion($aversion[1]);
				$this->setBrowser(self::BROWSER_FIREBIRD);
				$retval = true;
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is Firefox or not
		 * @return boolean True if the browser is Firefox otherwise false
		 */
		protected function checkBrowserFirefox() {
			$retval = false;
			if( eregi('Firefox',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Firefox'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_FIREFOX);
				$retval = true;
			}
			return $retval;
		}
		
		/**
		 * Determine if the browser is Mozilla or not
		 * @return boolean True if the browser is Mozilla otherwise false
		 */
		protected function checkBrowserMozilla() {
			$retval = false;
			if( eregi('Mozilla',$this->_agent) && eregi('rv:[0-9].[0-9][a-b]',$this->_agent) && !eregi('netscape',$this->_agent)) {
				$aversion = explode(' ',stristr($this->_agent,'rv:'));
				eregi('rv:[0-9].[0-9][a-b]',$this->_agent,$aversion);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_MOZILLA);
				$retval = true;
			}
			else if( eregi('mozilla',$this->_agent) && eregi('rv:[0-9]\.[0-9]',$this->_agent) && !eregi('netscape',$this->_agent) ) {
				$aversion = explode(" ",stristr($this->_agent,'rv:'));
            	eregi('rv:[0-9]\.[0-9]\.[0-9]',$this->_agent,$aversion);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_MOZILLA);
				$retval = true;
			}
			return $retval;
		}

		/**
		 * Determine if the browser is Lynx or not
		 * @return boolean True if the browser is Lynx otherwise false
		 */
		protected function checkBrowserLynx() {
			$retval = false;
			if( eregi('libwww',$this->_agent) && eregi("lynx", $this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Lynx'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_LYNX);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is Amaya or not
		 * @return boolean True if the browser is Amaya otherwise false
		 */
		protected function checkBrowserAmaya() {
			$retval = false;
			if( eregi('libwww',$this->_agent) && eregi("amaya", $this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Amaya'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_AMAYA);
				$retval = true;
			}
			return $retval;
		}
			
		/**
		 * Determine if the browser is Chrome or not
		 * @return boolean True if the browser is Safari otherwise false
		 */
		protected function checkBrowserChrome() {
			$retval = false;
			if( eregi('Chrome',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Chrome'));
				$aversion = explode(' ',$aresult[1]);
				$this->setVersion($aversion[0]);
				$this->setBrowser(self::BROWSER_CHROME);
				$retval = true;
			}
			return $retval;
		}		
		
		/**
		 * Determine if the browser is Safari or not
		 * @return boolean True if the browser is Safari otherwise false
		 */
		protected function checkBrowserSafari() {
			$retval = false;
			if( eregi('Safari',$this->_agent) && ! eregi('iPhone',$this->_agent) && ! eregi('iPod',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Version'));
				if( isset($aresult[1]) ) {
					$aversion = explode(' ',$aresult[1]);
					$this->setVersion($aversion[0]);
				}
				else {
					$this->setVersion(self::VERSION_UNKNOWN);
				}
				$this->setBrowser(self::BROWSER_SAFARI);
				$retval = true;
			}
			return $retval;
		}		
		
		/**
		 * Determine if the browser is iPhone or not
		 * @return boolean True if the browser is iPhone otherwise false
		 */
		protected function checkBrowseriPhone() {
			$retval = false;
			if( eregi('iPhone',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Version'));
				if( isset($aresult[1]) ) {
					$aversion = explode(' ',$aresult[1]);
					$this->setVersion($aversion[0]);
				}
				else {
					$this->setVersion(self::VERSION_UNKNOWN);
				}
				$this->setBrowser(self::BROWSER_IPHONE);
				$retval = true;
			}
			return $retval;
		}		

		/**
		 * Determine if the browser is iPod or not
		 * @return boolean True if the browser is iPod otherwise false
		 */
		protected function checkBrowseriPod() {
			$retval = false;
			if( eregi('iPod',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Version'));
				if( isset($aresult[1]) ) {
					$aversion = explode(' ',$aresult[1]);
					$this->setVersion($aversion[0]);
				}
				else {
					$this->setVersion(self::VERSION_UNKNOWN);
				}
				$this->setBrowser(self::BROWSER_IPOD);
				$retval = true;
			}
			return $retval;
		}		

		/**
		 * Determine if the browser is Android or not
		 * @return boolean True if the browser is Android otherwise false
		 */
		protected function checkBrowserAndroid() {
			$retval = false;
			if( eregi('Android',$this->_agent) ) {
				$aresult = explode('/',stristr($this->_agent,'Version'));
				if( isset($aresult[1]) ) {
					$aversion = explode(' ',$aresult[1]);
					$this->setVersion($aversion[0]);
				}
				else {
					$this->setVersion(self::VERSION_UNKNOWN);
				}
				$this->setBrowser(self::BROWSER_ANDROID);
				$retval = true;
			}
			return $retval;
		}		

		/**
		 * Determine the user's platform
		 */
		protected function checkPlatform() {
			if( eregi("iPhone", $this->_agent) ) {
				$this->_platform = self::PLATFORM_IPHONE;
			}
			else if( eregi("iPod", $this->_agent) ) {
				$this->_platform = self::PLATFORM_IPOD;
			}
			else if( eregi("win", $this->_agent) ) {
				$this->_platform = self::PLATFORM_WINDOWS;
			}
			elseif( eregi("mac", $this->_agent) ) {
				$this->_platform = self::PLATFORM_APPLE;
			}
			elseif( eregi("linux", $this->_agent) ) {
				$this->_platform = self::PLATFORM_LINUX;
			}
			elseif( eregi("OS/2", $this->_agent) ) {
				$this->_platform = self::PLATFORM_OS2;
			}
			elseif( eregi("BeOS", $this->_agent) ) {
				$this->_platform = self::PLATFORM_BEOS;
			}
		}
	}
?>
