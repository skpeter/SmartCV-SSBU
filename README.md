# SmartCV-SSBU

https://github.com/user-attachments/assets/f1c46930-3639-43b1-b6b0-a7d512f58d5a

SmartCV-SSBU is a tool designed to provide data on Super Smash Bros. Ultimate matches without the need for installing mods on your Nintendo Switch, or the need for a powerful PC to read game data in real time. 

It's a project that uses pixel detection to recognize certain situations in the game to take the opportunity to read data from using OCR. Due to this, it's able to gather enough data to report the results on a match (some assumptions given). Look for the **How does it work?** section to get a more in-depth explanation.

## Requirements
- [OBS (does not necessarily need to be streaming)](https://obsproject.com/download)
- [Advanced Scene Switcher OBS Plugin](https://github.com/WarmUpTill/SceneSwitcher/releases)
- Your copy of Super Smash Bros. Ultimate must be in **English** (other languages coming soon)

## Step 1: Installation
- Follow either one of the two steps below:
### Step 1.1: Installing the CPU version
- Installing the CPU version is very easy. Just download the compiled release.zip [here](https://github.com/skpeter/smartcv-ssbu/releases).
- You can skip to step 2 from here.
### Step 1.2: Installing the GPU version
- You will need to download the **source code** zip [here](https://github.com/skpeter/smartcv/releases).
- Install Python if you haven't done so already [here](https://www.python.org/downloads/). **Recommended version is 3.12**.
- Open a command prompt terminal on the installed directory and type `pip install -r requirements.txt`
- You will need to then install PyTorch, which is done through command prompt/terminal. Go to Pytorch's "Start Locally" section [here](https://pytorch.org/get-started/locally/), pick the **Stable** build, select the OS you use (**Windows, Mac or Linux**), **Pip** as packaging system, **Python** as language and then select the **Compute Platform** available on your GPU. You can check which version of CUDA your GPU supports [here](https://en.wikipedia.org/wiki/CUDA#GPUs_supported).
![PyTorch installation page](img/install1.jpg)
- - Choosing these options will generate a command that you should copy and paste on your terminal/command prompt. PyTorch weighs around 3GB, so take your time.

## Step 2: Setup
SmartCV reads game data directly from the OBS video source you put it on through OBS Websockets. **Make sure you have OBS Websocket enabled and configured before continuing**. Open your `config.ini` file, find a setting called `source_title`, insert the name of your OBS source, and that's it! Make sure the other OBS settings are correct so SmartCV can connect with OBS. `width` and `height` are the resolution of the image OBS sends. If you want to save up on some CPU usage, you can lower this resolution (as long as it's 16:9 aspect ration), however some things may not behave like normal if you do.

### Step 3: Usage
- To run the GPU version of the app, open the `smartcv.bat` file. To run the CPU version just open `smartcv.exe`.
**From here all you need to do is follow the on-screen instructions for the game detection to start.**
**If using OBS, make sure it is open and do not disable the game capture source!**

## Troubleshooting
- **When I run the app it says a bunch of code that ends with `ModuleNotFoundError: No module named 'torch'"` at the end! What do I do?**

Try restarting your system. If that doesn't work, append `py -m` to the code that installs PyTorch. For example: `py -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

## Where do I use this?
SmartCV opens a websocket server (on port 6565 by default) to send data to.
As of this writing, only [S.M.A.R.T.](https://skpeter.github.io/smart-user-guide) has integrations to it. If you want to integrate SmartCV into your own app, you can look at what the data output looks like on the example JSON files.

## Known Issues

- The app doesn't know how to differentiate handwarmers from actual matches. [S.M.A.R.T.](https://skpeter.github.io/smart-user-guide) (the companion app) has a workaround for this at the moment.

## How does it work?

Explanation coming soon

## Check out also:
- [SmartCV-RoA2 for Rivals of Aether II](https://github.com/skpeter/SmartCV-RoA2)

## Contact

[I am mostly available on my team's Discord Server if you'd like to talk about SmartCV or have any additional questions.](https://discord.gg/zecMKvF8b5)
