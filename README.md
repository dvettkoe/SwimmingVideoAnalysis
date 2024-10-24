# Swimming Video Analysis

## Overview
An open-source python-based program for the analysis of swimming cycles of _C. elegans_. Using Swimming Video Analysis allows to combine and delete tracks after automated tracking by "wrMTrck". The software opens annotated video files and displays respective tracks. It allows to find specific tracks anywhere in the video only by a click of the user.

## Getting started

### Installation

Download the [latest release](), unzip the folder and start the _SwimmingVideoAnalysis.exe"_.

### How to use Swimming Video Analysis

#### 1. Analyse videos using wrMTrck

Analyze your videos of swimming _C. elegans_ using the ImageJ Plugins **wrMTrck** (https://www.phage.dk/plugins/wrmtrck.html).

**Important**: 


Add a "1" to the "rawData" field to include output of X-& Y-Coordinates - this is mandatory for the script to run later on. 
After wrMTrck is done re-open the "*_labels_compressed.AVI" file in ImageJ and save it again as AVI but change compression type to JPEG.

For an **easy way** to run wrMTrck with the optimal setting (rawData & compression type "JPEG") as a batch for multiple videos/folders at once, download the ["wrMTrck_ROI_Batch.txt"]() from this repository and include it into the wrMTrck plugin folder in your ImageJ. 

#### 2. Start Swimming Video Analysis

Start the _SwimmingVideoAnalysis.exe"_ and click on “Select folder” and select a subfolder of one measurement, which contains the videos.

Example:

>	    main folder -> subfolder for condition 1 -> videos of condition 1
>	
>                   -> subfolder for condition 2 -> videos of condition 2
>				        	
>                   ...
>					        
>                   -> subfolder for condition n -> videos of condition n 

If the subfolder contains multiple videos, the software should load the first video into the left panel (The number of videos in the folder loaded is indicated on the top in the right corner.)

### Video functions

The user can use the slider under the video to go through the frames. The slider on the left side can be used to zoom into the video. 
Holding left-click pressed inside of the video allows to pan through the video.

Jumping to a specific frame is possible by typing the frame number into the entry field and pressing the "Jump to Frame button"

### Table functions

The table on the right contrians the following columns:

**Track**: These numbers are displayed in the video next to the respective worm.

**#Frames**: Those are the numbers of frames the worm was tracked

**1stFrame**: This is the frame number when the “Track” first appears. Most of the time for the first Tracks it is 0 but the higher the track number, this number increase as the track appears later in the video.

**time(s)**: The duration one worm was tracked. The best-case scenario would be the video duration (or close to the video duration).

**Bends**: The number of body bends of this worm.

**BBPS**: The number of body bends per second for this worm.

#### Combine Tracks

Here one can input the Track number of a worm that gets lost or crosses another worm and gets a new track number afterwards. Input them like this 2,23,46 and press “Combine”. (Just separate the numbers using comma without spaces)

Scroll through the video and check every worm that was not tracked the whole time (check in the column “#Frames or time(s)”.
If you see that a worm was tracked less then the video duration look for it in the video and follow it by going through all frames. Some worms are lost by the software and just get a new number (and sometimes more than once). 
Sometimes worms cross each other and get a new track number assigned to them afterwards. In both cases input the first number and each following new assigned number and then press the combine button. The table should now show the first track number and you will see that the #Frames is now higher (best case scenario would be that it is now the same as a worm tracked the whole time, but it is most likely still lower. However, you have gained some more data for this worm by combining all of its alternative numbers as it sums their Bends).

> **Careful: Should the #Frames or time(s) exceed the video duration, most likely a wrong number was input and wrong tracks combined together. In this case, click on the “undo” button. However, this button can only undo ONE input. If you see it after combining another track, it is not possible to undo it and this video need to be re-analyzed again. See the note for this on the bottom<sup>1</sup>.**
>
> **So be careful and check after each combining step!**


https://github.com/user-attachments/assets/919fe834-2c3f-4760-a941-4ff449b16037


#### Search Tracks

Sometimes worms are not in the first frame (1stFrame cell says at which frame they appear). It can be a hassle to find a specific worm number. In this case zoom out a bit, so that you can see all worms and double click the Track number (left column in light grey) you want to find. In the video you should see a red circle that shows where this worm is located, should it appear first in a different frame it will jump to one frame where the track number can be found.


https://github.com/user-attachments/assets/a6548de8-3ab5-4938-a019-b4037d415d11


Alternatively, the searched for track number can be input in the respective field under the video.

#### Delete tracks

Input track numbers of tracked objects that are no worms or worms that cross each other and have a track number assigned (Two worms are kind of on top of each other). Input the number of the track to delete and press the “Delete” button. If one wants to delete more tracks at a time, separate the numbers by comma just as for the “Combine tracks” button.  Please verify that you deleted the right tracks in case you need to undo this action. (Along with the Main Application a console window appears that “logs” all you input).

>Example: Worm 3 and 4 cross each other and swim together for 30 frames. During this time, they get one number assigned in this example it is 42. After the separate again worm 3 gets the number 45 and worm 4 the number 46. In this case you need to delete number 42 as it is assigned for both of them and most likely produces wrong Bends. Afterwards you would combine 3 and 45, as well as 4 and 46.

Additionally, some objects like small filaments can be tracked as worms and produce a high number of bends or none. These could be tracked throughout the whole video or just for a few seconds. Delete those numbers, too.


https://github.com/user-attachments/assets/36272dd8-e979-4caf-8b93-c1f98c22a801


#### Save & Proceed

After combining everything that should be one track and deleting all artifacts, click on “Save&Proceed” to open the next video.

#### Save & Exit

If you want to end the analysis after you are done with one video you can also click “Save&Exit”.
You can pick up where you end the analysis by loading the same folder, but it will always start with the first video. Just make a note of the last video you analyzed (you can see the number in the right corner at the top) and click on “Save&Proceed” until you are at your desired video number.


#### 3. Repeat for remaining folders containing videos

Load the next folder and repeat all steps above until all folders containing videos are processed.

#### 4. Post-Processing

If you are done with all folders you can process them to make it easier for graphing. Click on the “Open Postprocessing” button. 


You are asked to input a folder for postprocessing. Create a new folder for this with subfolders for each measurement. Inside copy the “tracks_processed” folders you find in each of the previously analyzed folders. A detailed instruction about how to structure this postprocessing folder can be found by clicking (and holding the button clicked) blue “i” icon in the Postprocessing field.

#### Notes

<sup>1</sup>Should you have combined wrong tracks or deleted wrong tracks and have noticed later then one step, you cannot undo it within the program. Instead, note the number (and name can be seen above the video window) of video you are analyzing and close the program. Now go to the directory which you analyzed in your file browser and locate the two following files: “x_tracks.txt.temp.xlsx” and “x_tracks.txt.temp_undo.xlsx” for the video you made a mistake. Delete both files. Afterwards, go into the “tracks_processed” folder of this directory and open the “x_log.txt” file. Here you find every step you have done protocolled. You can now copy the numbers you want to combine or delete after opening the video in the program again. This will save you time as you do not have analyze the whole video from the beginning (although you still have to to all steps again, but they are documented). Just make sure to skip the step you did an error. 
(“x” equals the name of the video)







