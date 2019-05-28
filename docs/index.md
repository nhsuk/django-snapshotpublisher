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
    * `api_django` (string) define the response format from api, possible value 'json' & 'django'
        * `json` the api will return result in json format
        * `django` the api will return result as python dictionary (that can contains django queryset)

### add_content_release
```python
add_content_release(site_code, title, version, parameters=None, based_on_release_uuid=None, use_current_live_as_base_release=False)
```
Add a new content release for the passed details and returns a unique reference for the release.
* Description for specifque configuration
    * SQL:
        * Create new Release record
        * If basedOnReleaseUuid not None, copy all children from old release to new release.
* paramaters
    * site_code (string)
    * title (string)
    * version (string)
    * paramaters (dict, optional) store extra parameters for for a ContentRelease eg: `{'frontend_id': 'v0.1', 'domain': 'test.co.uk'}`
    * based_on_release_uuid (uuid, optional)
    * use_current_live_as_base_release (bool, optional)
* response:
```python
{
    'status': 'success',
    'content': <ContentRelease: title1>
}
```

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
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success'
}
```

### update_content_release
```python
update_content_release(site_code, release_uuid, title=None, version=None, parameters=None)
```
Updates the content release title or/and version. If title or version is None, it doesn't do anything
* Description for specifque configuration
    * SQL: Update the title/version field in the Release record
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * title (string, optional)
    * version (string, optional)
    * paramaters (dict, optional)
* response:
```python
{
    'status': 'success'
}
```

### update_content_release_parameters
```python
update_content_release_parameters(site_code, release_uuid, parameters, clear_first=False)
```
Updates the content release extra parameters
* Description for specifque configuration
    * SQL: Update the key and content field in the ContentReleaseExtraParameter record
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * paramaters (dict, optional)
    * clear_first (bool, optional) if True, remove all the existing extra parameter for the ContentRelease beofre adding the other one
* response:
```python
{
    'status': 'success'
}
```

### get_extra_paramater
```python
get_extra_paramater(site_code, release_uuid, key)
```
Get a content release extra parameter
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * key (string)
* response:
```python
{
    'status': 'success',
    'content': 'v0.1'
}
```

### get_extra_paramaters
```python
get_extra_paramaters(site_code, release_uuid)
```
Get all content release extra parameters
* paramaters
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success',
    'content': <QuerySet [
        <ContentReleaseExtraParameter: ContentReleaseExtraParameter object (18)>,
        <ContentReleaseExtraParameter: ContentReleaseExtraParameter object (17)>
    ]>
}
```

### get_content_release_details
```python
get_content_release_details(site_code, release_uuid, parameters=None)
```
Return details for a given content release.
* Description for specifque configuration
    * SQL: Return the Release object for the given siteCode and releaseUuid
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * paramaters (dict, optional)
* response:
```python
{
    'status': 'success',
    'content': <ContentRelease: title1>
}
```

### get_content_release_details_query_parameters
```python
get_content_release_details_query_parameters(site_code, parameters)
```
Get release for given paramters
* paramaters
    * site_code (string)
    * paramaters (dict, optional)
* response:
```python
{
    'status': 'success',
    'content': <ContentRelease: title1>
}
```

### get_live_content_release
```python
get_live_content_release(site_code, parameters=None)
```
Returns details for the current live content release.
* paramaters
    * site_code (string)
    * paramaters (dict, optional)
* response:
```python
{
    'status': 'success',
    'content': {
        'uuid': '7aa81f8e-3b95-418f-913c-af5838777781',
        'version': '0.0.1',
        'title': 'title1',
        'site_code': 'site1',
        'status': 'FROZEN',
        'publish_datetime': '2019-05-28T12:33:00.281Z',
        'use_current_live_as_base_release': False,
        'base_release': None
    }
}
```

### set_live_content_release
```python
set_live_content_release(site_code, release_uuid)
```
Set publish_datetime to now and freeze the given content release.
* paramaters
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success'
}
```

### freeze_content_release
```python
freeze_content_release(site_code, release_uuid, publish_datetime)
```
Set publish_date to the given publish_date and freeze the given content release.
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * publish_datetime: format eg: '2018-09-01T13:20:30+0300'
* response:
```python
{
    'status': 'success'
}
```

### unfreeze_content_release
```python
unfreeze_content_release(site_code, release_uuid)
```
Set to Pending the given content release if not published.
* paramaters
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success'
}
```

### archive_content_release
```python
archive_content_release(site_code, release_uuid)
```
Set to Archived the given content release if the content release is live and frozen (else return an error_msg)
* paramaters
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success'
}
```


### unarchive_content_release
```python
unarchive_content_release(site_code, release_uuid)
```
Unarchived a content release that was archived
* paramaters
    * site_code (string)
    * release_uuid (uuid)
* response:
```python
{
    'status': 'success'
}
```

### list_content_releases
```python
list_content_releases(site_code, status=None)
```
Returns a list of content releases for the given site (and status if define).
* Description for specifque configuration
    * SQL: Return Releases matching <siteCode> and <status>
* paramaters
    * site_code (string)
    * status (int, optional)
* response:
```python
{
    'status': 'success',
    'content': <QuerySet [
        <ContentRelease: title2>,
        <ContentRelease: title1>
    ]>
}
```

### get_document_from_content_release
```python
get_document_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Returns document json content for the given documentKey in a content release.
* Description for specifque configuration
    * SQL: Fetch the ReleaseDocument record containing the json with id documentKey and return the json content field.
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * document_key (string)
    * content_type (string, optional, default='content')
* response:
```python
{
    'status': 'success',
    'content': <ReleaseDocument: content - key1>
}
```

### get_document_extra_from_content_release
```python
get_document_extra_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Returns document extra parameters json content for the given documentKey in a content release.
* Description for specifque configuration
    * SQL: Fetch the ReleaseDocument record containing the json with id documentKey and return the json content field.
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * document_key (string)
    * content_type (string, optional, default='content')
* response:
```python
{
    'status': 'success',
    'content': [
        {
            'key': 'para2',
            'content': 'test2'
        }, {
            'key': 'para1',
            'content': 'test1'
        }
    ]
}
```

### publish_document_to_content_release
```python
publish_document_to_content_release(site_code, release_uuid, document_json, document_key, content_type='content', parameters=None)
```
Publishes the given document to a content release. Return create: True if it's a new record else, return false it's it's a record that have been updated.
* Description for specifque configuration
    * SQL: Create a ReleaseDocument record containing the documentJson with id documentKey
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * document_json (string)
    * document_key (string)
    * content_type (string, optional, default='content')
    * paramaters (dict, optional)
* response:
```python
{
    'status': 'success',
    'content': {
        'created': True
    }
}
```

### unpublish_document_from_content_release
```python
unpublish_document_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Unpublish document from the given content release, removing any associated artefacts.
* Description for specifque configuration
    * SQL: Remove the ReleaseDocument record containing with id documentKey
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * document_key (string)
    * content_type (string, optional, default='content')
* response:
```python
{
    'status': 'success'
}
```

### delete_document_from_content_release
```python
delete_document_from_content_release(site_code, release_uuid, document_key, content_type='content')
```
Remove document from the given content release and won't import the corresponding document from his base content release.
* Description for specifque configuration
    * SQL: Create or Update ReleaseDocument with not document_json and deleted set to True
* paramaters
    * site_code (string)
    * release_uuid (uuid)
    * document_key (string)
    * content_type (string, optional, default='content')
* response:
```python
{
    'status': 'success'
}
```

### compare_content_releases
```python
compare_content_releases(site_code, my_release_uuid, compare_to_release_uuid)
```
Compare documents for a content release to the documents from another content release.
* paramaters
    * site_code (string)
    * my_release_uuid (uuid)
    * compare_to_release_uuid (uuid)
* response:
```python
{
    'status': 'success',
    'content': [
        {
            'document_key': 'key3',
            'content_type': 'content',
            'diff': 'Added',
            'parameters': {
                'p2': 'test8',
                'p1': 'test7'
            }
        },{
            'document_key': 'key2',
            'content_type': 'content',
            'diff': 'Changed',
            'parameters': {
                'release_from': {
                    'p2': 'test6',
                    'p1': 'test5'
                },
                'release_compare_to': {
                    'p2': 'test4',
                    'p1': 'test3'
                }
            }
        }, {
            'document_key': 'key1',
            'content_type': 'content',
            'diff': 'Removed',
            'parameters': {
                'p2': 'test2',
                'p1': 'test1'
            }
        }
    ]
}
```