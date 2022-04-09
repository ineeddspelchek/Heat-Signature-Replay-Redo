## CRUCIALLY IMPORTANT
Until it is fixed, do not run for recordings longer than about 30 seconds as it will freeze and ***likely crash*** your computer. This is being published to get help with fixing not yet for practical use.

# Heat-Signature-Replay-Redo
streamlined program to record and edit Heat Signature clips into realtime speed 

## Credits
Much of this comes thanks to two people:
* Random Davis (www.youtube.com/user/r2blend) for his interface for reading memory with Python, and
* @DurryQuill from the Suspicious Developments Discord who found the in-game variable address that makes this entire program possible to begin with

A code snippet was also adapted from www.thepythoncode.com/article/make-screen-recorder-python.

# How To
1. Download python.
2. Download the two python programs.
3. Edit the top 4 variables of `heatSigReplay.py` to your preference.
4. Download the necessary dependencies by putting the following into command prompt:
~~~~
pip install ReadWriteMemory
pip install pymem
pip install cv2
pip install numpy
pip install pyautogui
pip install mss
pip install pynput
pip install moviepy
~~~~
5. Run `heatSigReplay.py`
