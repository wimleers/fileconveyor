# 0.2-dev — October 15, 2012

Critical bugfixes. Prevent file loss and makes Rackspace Cloud Files operational again.

* Minor bug: #122: PendingDeprecationWarning/global name 'ConnectionError' is not defined
* Critical bug: #118: django-storage's `mosso` back-end was deprecated in favor of `django-cumulus`, so migrated to `django-cumulus`
* Critical bug: #108: When no `fileDeletionDelayAfterSync` attribute is set, no deletion should happen at all
* Bug: #103: Error in setup.py when using Python 2.5

# 0.1-dev — January 21, 2012

Initial `pip`-powered release. Major thanks to @benoitbryon!
