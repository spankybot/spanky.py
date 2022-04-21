Data 2.0 Design Proposal
========================

Why?
====
- `plugin_data` and the storage.py systems are 'hacks' that have been made standard;
- storage.py is especially bad, it's built on dicts with no type safety! At any moment, an error can occur or 



What
====

- A new `resources.py` manager for file-based data; 
- A sqlite-based storage system. Still haven't decided wether to use the sqlite package or sqlalchemy

Nice-to-haves
=============

- An easier way to convert old schemas to sqlite.