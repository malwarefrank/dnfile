=======================
dnfile design decisions
=======================


Main
----

* Everything is a class.
* Store raw structure values in struct attribute.
* Store parsed struture values in object attributes.
* Parse as much as we can, even if the file is malformed.
* Easy to use.  Developed with IDE autocompletion in mind.
* Base CLR classes should not need to know anything about PE objects.


Naming
------

* corhdr.h definitions in classes named Cor*
* bases classes prefixed with Clr


