# Usage

## User Management

When logged in, users will see a "User management" button appear in the top right of the navbar.

![User Management Button](./images/usage/user_management/button.png "User Management Button")

The pop-up allows users to quickly change the global filtering of all projects or a specific individual project, access their upload token for uploading candidates, or to change their password.

![User Management Modal](./images/usage/user_management/modal.png "User Management Modal")

Please note that the filtering by projects is only saved in the user session data and will be forgotten when the user logs out of the web application.

## Candidates

The "Candidates" page is where users can filter (within all or a selected project) by observation, beam, deep number, cone searches (candidate, beam, and/or deep coordinates, all in separation in arcmin), or by any of the various float values that were uploaded with the candidate.

When filtering with the float sliders, they will _only_ show candidates with values between the requested minimums and maximums from sliders. They will exclude candidates that have "nan" or "inf" values for that particular variable. However, the unfiltered defaults will show candidates with all values.

![Candidate Table - Filtering](./images/usage/candidate_table/filtering.png "Candidate Table - Filtering")

Users can sort the filtered results by the columns of the table by clicking on the column header for that variable/column, in either ascending or descending order. Sorting of the filtered candidate results currently only works for the list presented on the page, not for all the paginated results.

![Candidate Table - Results](./images/usage/candidate_table/results.png "Candidate Table - Results")

Navigating to a filtered candidate summary page is done by clicking on the "name" of the candidate.

## Candidate Rating

### Summary

When clicking on the name of a candidate from the Candidates page, users will be directed to the page `/candidate_rating/<candidate_hash_id>`. Users will be shown a summary of all candidate data, the deep image and slices gif (if uploaded), a plot in Apache Echarts of the peak lightcurve data, the Aladin Lite plugin (pointed to the candidate coordinates), and the relevant statistical maps of the beam.

![Rate Candidate - Summary](./images/usage/rate_candidate/summary.png "Rate Candidate Summary")

Users will also be able to pause, play and select individual frames using the slider for the slices gif.

All the data is available to download for the candidate and beam from this page, either being the slices fits, deep fits, Lightcurve Peak Flux CSV (with RMS error) and along with the beam STD, Peak, and Chisquared fits files (at the bottom of the page). Download buttons on the page will only be present if there were files uploaded with the candidate data using the upload script.

### Nearby Objects Search

Users are able to search for nearby objects of x (float) arcmin radius about the candidates coordinates. The webapp queries the ATNF Pulsar database (saved locally for quick access), using a web request to retrieve results from [SIMBAD](https://simbad.u-strasbg.fr/simbad/sim-fcoo), as well as searches the local database (filtered by the same project/s selected from the User Management model). Please note that the search will take longer to load when requesting a relatively large arcmin radius.

![Rate Candidate - Nearby Objects](images/usage/rate_candidate/nearby_objects.png "Rate Candidate Nearby Objects")

Users are also able to sort these results by ascending or descending order, but are ordered by ascending separation of arc-minutes from the candidate by default.

### Rating

On the right side of the candidate rating page, there is the sticky ratings modal that allows users to rate a candidate by selecting a specific "Tag" by using the dropdown form and selecting the options of "True", "False", or "Unsure", as well as adding any notes to the rating.

![Rate Candidate - Modal](images/usage/rate_candidate/modal.png "Rate Candidate Modal")

Once rated, users will be able to see their previous rating of the candidate, and click on the the "Next unrated random candidate" which will redirect the user to a random candidate within the same selected project or all projects. Users can only create one rating per candidate but have the option of updating their previous rating if required.

![Rate Candidate Already Rated](images/usage/rate_candidate/already_rated.png "Rate Candidate Already Rated")

### Creating a Classification Tag

If a suitable classification tag is not present for a particular candidate, users can choose to create a new tag if required by clicking on the green "+" button and the following modal will show:

![Rate Candidate - Create Tag](images/usage/rate_candidate/create_tag.png "Rate Candidate Create Tag")

Please note that the web application has a number of tags loaded by default on initial startup. This list can be found in the Django database migration file:

`ywangvaster_webapp/candidate_app/migrations/0005_create_tags.py`

Classification tags are global and can be accessed for all projects and users. At the moment, tags can only be deleted from the Django admin page.

## Ratings Summary

On this page users can see an overview of all the ratings that have been submitted for candidates by all other users. These ratings are also filtered by project like the rest of the web application.

The two Echarts plots are simple bar charts for the counts of 'Ratings per User' and 'Ratings per Classification Tag'. These plots are produced from the filtering form below and will change if the user chooses to filter for observation, tag, confidence, etc.

![Ratings Summary - Summary](images/usage/ratings_summary/summary.png)

The filtered ratings (from the form) can be downloaded in CSV form using the "Download filtered ratings" button. This will download a zip file that contains all of the tags and notes for each tag in a `tags.csv`, as well as the filtered ratings data in a `ratings.csv` file. The filtered rating results also populate the above bar chart plots.

![Ratings Summary - Results](images/usage/ratings_summary/results.png)

Users that have staff privileges will be able to delete individual rating records, which is done by clicking on the rubbish bin icon on the left most column of the ratings table. This deletion is permanent and there is no way to recover the deleted record.

## Site Admin

Only users that have staff privileges will be able to see this page. They will be presented with a list of projects and a observations that were uploaded for each project. The table details the space used on the host machine of the total in gigabytes.

Each table is for each project that's been created and the observations under each project is listed. Users will be able to see the observation ID (SBID), the user that uploaded the data, the upload date, the number of beams in the observation, the total number of candidates in the observation, the number of candidates that have been rated, the total number of ratings (from all users), the space used and the number files of the observation.

Deleting individual observations can be done by clicking on the rubbish bin icon on the left most column. Similarly, users can delete for the project and all of the observations in the project. Please note that this will delete all relevant data to the project, including ratings. The deletion is permanent and accidentally deleted data cannot be recovered.

![Site Admin](images/usage/site_admin/site_admin.png)
