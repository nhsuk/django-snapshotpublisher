Django Snapshot Publisher Package Functional Specification
==========================================================

This package is a generic way of managing and publishing content to release snapshots that can be used to generate a completely consistent 'edition' of a website.

Class: PublisherAPI
-------------------

All results will return return a status_code and contains a content or error_msg attributes.

Successfull call to the api:
```python
{
  'status': 'success',
  'content': {
    ...
  }
}
```
In the documentation we only define what will be return in the content attribute

Call to the api that fail:
```python
{
  'status': 'error',
  'error_code': 'content_release_already_exists',
  'error_msg': 'ContentRelease already exists'
}
```

PublisherAPI Calls
------------------

### Contructor
```python
PublisherAPI(api_django='django')
```
* paramaters
    * `api_django` define the response format from api, possible value 'json' & 'django'
        * `json` the api will return result in json format
        * `django` the api will return result as python dictionary (that can contains django queryset)

### add_content_release
```python
add_content_release(site_code, title, version, based_on_release_uuid=None)
```
Add a new content release for the passed details and returns a unique reference for the release.
* Description for specifque configuration
    * SQL:
        * Create new Release record
        * If basedOnReleaseUuid not None, copy all children from old release to new release.
* paramaters
    * site_code
    * title
    * version
    * based_on_release_uuid (optional)
* response [TODO]

### remove_content_release(site_code, release_uuid)
```python
remove_content_release(site_code, release_uuid)
```
Removes the content release and any associated artefacts for the given site and release reference.
* Description for specifque configuration
    * SQL:
        * Remove the Release record
        * Remove the children of the Release.
* paramaters
    * site_code
    * release_uuid
* response [TODO]

### update_content_release
```python
update_content_release(site_code, release_uuid, title=None, version=None)
```
Updates the content release title or/and version. If title or version is None, it doesn't do anything
* Description for specifque configuration
    * SQL: Update the title/version field in the Release record
* paramaters
    * site_code
    * release_uuid
    * title (optional)
    * version (optional)
* response [TODO]

### get_content_release_details(site_code, release_uuid)
```python
get_content_release_details(site_code, release_uuid)
```
Return details for a given content release.
* Description for specifque configuration
    * SQL: Return the Release object for the given siteCode and releaseUuid
* paramaters
    * site_code
    * release_uuid
* response[TODO]
    * content_release

### get_live_content_release
```python
get_live_content_release(site_code)
```
Returns details for the current live content release.
* paramaters
    * site_code
* response [TODO]
    * content_release

### set_live_content_release
```python
set_live_content_release(site_code, release_uuid)
```
Set publish_datetime to now and freeze the given content release.
* paramaters
    * site_code
    * release_uuid
* response [TODO]

### freeze_content_release
```python
freeze_content_release(site_code, release_uuid, publish_datetime)
```
Set publish_date to the given publish_date and freeze the given content release.
* paramaters
    * publish_datetime: format eg: '2018-09-01T13:20:30+0300'
* response [TODO]

### unfreeze_content_release
```python
unfreeze_content_release(site_code, release_uuid)
```
Set to Pending the given content release if not published.
* paramaters
    * site_code
    * release_uuid
* response [TODO]

### archive_content_release
```python
archive_content_release(site_code, release_uuid)
```
Set to Archived the given content release if the content release is live and frozen (else return an error_msg)
* paramaters
    * site_code
    * release_uuid
* response [TODO]


### unarchive_content_release
```python
unarchive_content_release(site_code, release_uuid)
```
Freeze the given content release if the content release is live and archived  (else return an error_msg)

### list_content_releases
```python
list_content_releases(site_code, status=None)
```
Returns a list of content releases for the given site (and status if define).
* Description for specifque configuration
    * SQL: Return Releases matching <siteCode> and <status>
* paramaters
    * site_code
    * status (OPTIONAL)
* response [TODO]
    * [ContentRelease]

### get_document_from_content_release
```python
get_document_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Returns document json content for the given documentKey in a content release.
* Description for specifque configuration
    * SQL: Fetch the ReleaseDocument record containing the json with id documentKey and return the json content field.
* paramaters
    * site_code
    * release_uuid
    * document_key
    * content_type (optional, default='content')
* response [TODO]
    * document_json

### publish_document_to_content_release
```python
publish_document_to_content_release(site_code, release_uuid, document_json, document_key, content_type='content')
```
Publishes the given document to a content release. Return create: True if it's a new record else, return false it's it's a record that have been updated.
* Description for specifque configuration
    * SQL: Create a ReleaseDocument record containing the documentJson with id documentKey
* paramaters
    * site_code
    * release_uuid
    * document_json
    * document_key
    * content_type (optional, default='content')
* response [TODO]
    * created

### unpublish_document_from_content_release
```python
unpublish_document_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Unpublish document from the given content release, removing any associated artefacts.
* Description for specifque configuration
    * SQL: Remove the ReleaseDocument record containing with id documentKey
* paramaters
    * site_code
    * release_uuid
    * document_key
    * content_type (optional, default='content')
* response [TODO]