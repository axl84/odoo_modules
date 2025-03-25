==========================
Chatter User Comment Only
==========================

This module filters chatter messages to show only those created by users while hiding system-generated messages.
It helps to maintain a clean and focused communication history by hiding automated notifications, emails, and logging messages.

Key Features
============

* Show only user-created messages in chatter
* Hide system-generated messages (automated emails, notifications, logging)
* Compatible with all Odoo models using chatter
* Simple configuration and setup

Configuration
=============

To use this module, you need to:

#. Install the module
#. No additional configuration is needed - it works out of the box

Usage
=====

After installation, the module automatically:

#. Shows all messages created by any user in chatter
#. Hides system-generated messages:
    * Automated email notifications
    * Change tracking logs
    * System notifications
    * Scheduled reminders
#. Works with all models that use chatter functionality

Technical Details
==================

Message Filtering
------------------

* User messages are preserved in the chatter
* System-generated messages are filtered out:
    * Automated notifications
    * Email notifications
    * Change tracking
    * System logs
* No impact on message creation or storage

Dependencies
-------------

* mail: Base mail module for chatter functionality

Bug Tracker
===========

Bugs are tracked on `Kitworks Support <https://kitworks.systems/requests>`_.
In case of trouble, please check there if your issue has already been reported.

Maintainer
----------

.. image:: https://kitworks.systems/logo.png
   :alt: Kitworks Systems
   :target: https://kitworks.systems

This module is maintained by Kitworks Systems.

We can provide you further Odoo Support, Odoo implementation, Odoo customization, Odoo 3rd Party development and integration software, consulting services. Our main goal is to provide the best quality product for you.

For any questions `contact us <mailto:support@kitworks.systems>`__.
