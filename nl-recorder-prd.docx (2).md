**NL RECORDER**

Product Requirements Document

Version 0.1  ·  June 2026  ·  Status: Draft

| Author | Nil Patel |
| :---- | :---- |
| Users | Individuals with low technical skill |

# **1\. Purpose & Problem Statement**

## **1.1 The Problem**

My dad wanted to screen record some things, so I tried to teach him the most-used screen recorder, OBS. With the outdated layout, multiple options, and a plethora of technical options, it was too complicated. This led me to think whether natural language could be used to build such software for Mac devices. 

Screen recording today requires users to navigate OS-level menus, select sources, manage audio routing, all before capturing a single frame. Not to mention multiple issues such as audio not being recorded, screen recording format not being optimal, and a complex UI to navigate.

## **1.2 Problem Being Solved**

1. Complex UI: current offerings such as OBS have a very high technical User Interface which don’t allow a large number of people to use them  
2. Multiple Sources: Need to parse through multiple audio sources, window inputs, and mic inputs to be able to extract the information you need  
3. Unreliable: I have had issues where I forget to enable the mic, or the audio isn’t being properly captured from the window source that I am recording from, causing frustration when I check the screen recording file and there is no audio. 

## **1.3 Impact**

| Goal | *A minimalist UI that allows the setup of a screen recorder to go from 5 minutes to 10 seconds* |
| :---: | :---- |

Solving this unlocks:

* A less frustrating user experience of needing to match source windows and worrying about audio not playing. 

* Lower onboarding friction/mental load when it comes to setting up for what you need to record. Ex: don’t need to check if audio is properly being recorded or not. 

## **1.4 Resources & References**

* AVFoundation screen capture docs: developer.apple.com/av-foundation

* ffmpeg AVFoundation input guide: ffmpeg.org/documentation.html

* Ollama: https://docs.ollama.com/api/introduction

# **2\. User Persona**

|   Non Technical Primary | Any individual, especially older people with less technical experience (age 40), who want a simple UI with natural language as their input and a flawless output of a screen recording based on what they described.  Pain points: Too many steps to start recording Audio routing is confusing (mic vs system) Wants recordings saved automatically without prompts |
| :---: | :---- |

Secondary persona: 

## **2.1 Why is this the best way to solve**

## **2.2 Other Competing Products**

# **3\. Functional Requirements**

## **3.1 App Launch & Window**

* The app opens as a single window, fixed at 860×520px.

* The window is non-resizable in P0 (resizable layout is a P1 enhancement).

* The app must not require a login or account in P0.

* Downloadable Software with a simple setup for Macs

## **3.2 Windows Panel (left sidebar)**

* The sidebar displays all currently open macOS windows, fetched at launch.

* Each item shows: app name, window title (truncated), and a thumbnail placeholder.

* Window list refreshes on app focus (not in real time).

## **3.2 Inputs/Outpus:**

* Input: “Record the YouTube video from the Chrome tab about transpose.”  
* Output: Starts recording the video 

## **3.3 Output Preview**

The preview panel occupies the right two-thirds of the top area.

**3.3.1 Idle state (not recording)**

* Shows a centered placeholder icon and text: "Describe what to record".

* Status dot is grey; status label reads "Ready".

**3.3.2 Recording state**

* Placeholder is hidden; a mock canvas panel is revealed.

* Status dot turns red and blinks at \~700ms intervals.

* Status label reads "Recording".

* Timeline bar at the bottom of the preview fills from left to right (animated).

**3.3.3 Post-recording state**

* Status dot returns to grey; status label reads "Saving…" then "Saved ✓".

* Timeline bar holds at 100%.

* A system dialog appears: "Recording saved" with the file path and an Open in Finder button.

## **3.4 Natural Language Input Bar**

The input bar sits at the bottom of the window and is always visible.

**Happy flows**

* User types a prompt containing "record", "start", or "capture" → recording begins.

* User types "stop", "done", or "finish" while recording is active → recording stops.

* User clicks the Record button → same as typing "record".

* Any other prompt while no recording is active → recording starts (default behavior until LLM layer is added).

* User presses Record  buttom-\> Starts recording based on natural language input

* User presses Stop button \-\> stops recording and saves file

**Unhappy flows**

* User presses Enter with an empty input → input field is focused; no action taken; no error shown.

* User types "stop" when not recording → input is accepted; nothing happens (no error).

* ffmpeg is not installed → recording fails immediately; error dialog shown: "ffmpeg not found. Install with: brew install ffmpeg".

* Screen Recording permission is denied → ffmpeg produces a black video; no in-app detection in v0.1. README documents this.

## **3.5 Record Button**

* Default state: blue background, label "● Record".

* Recording state: red background, label "■ Stop".

* Clicking toggles between start and stop.

## **3.6 Mic & System Audio Toggles**

| Button | Default state | Behavior |
| :---- | :---- | :---- |
| 🎙 Mic | Off (grey) | Toggles microphone audio capture on/off. When on: red tint border. |
| 🔊 System audio | On (blue tint) | Toggles system audio capture on/off. In v0.1, this is a UI-only toggle — full system audio capture requires BlackHole or similar virtual device. |

* Toggle state persists for the duration of the app session only (not saved to disk in v0.1).

* If the mic is off and system audio is off, the recording proceeds without an audio track.

## **3.7 Recording Output**

* Output format: MP4 (H.264 video, AAC audio where applicable).

* Output location: \~/Desktop/recording\_YYYYMMDD\_HHMMSS.mp4.

* Frame rate: 30 fps.

* Video codec: libx264, preset ultrafast, CRF 23\.

* Capture cursor: enabled.

* On recording completion, a native macOS dialog is shown with the file path and an "Open in Finder" option.

## **3.8 Versions:**

P0 (MVP):

- Takes in User input and records the screen based on the window/tabs mentioned in the user's response \-\> using Ollama as the natural language processor  
- Has start and stop buttons for screen recording   
- Also records the audio on the screen  
- After the user puts in the input and the window to be recorded is identified, there is a preview of the screen/window being recorded on the app screen  
- On the left side of the app screen, there is a scrollable window of all the tabs open

P1 \- Enhancements

- If the user never asks for Mic or mentions audio, it double-checks with the user  
- Has a mic on/off button to record the computer mic  
- Has an input to decide if you want to record tab/window audio or not  
- On the bottom, have a bar which shows various audio inputs similar to OBS  
- ![][image1]


  
P2 \- Nice to Have:

- 

# **4\. Non-Functional Requirements**

| Requirement | Specification |
| :---- | :---- |
| Startup time | App window visible within 1.5s of launch on Apple Silicon. |
| Time to first frame | Recording must begin (ffmpeg process started) within 2s of user triggering record. |
| CPU usage (idle) | \< 2% CPU when app is open but not recording. |
| CPU usage (recording) | \< 25% CPU on M-series chips at 30fps, 1080p. |
| macOS compatibility | macOS 12 Monterey and above. |
|  |  |
|  |  |
|  |  |
|  |  |

# **5\. Testing Plan & Acceptance Criteria**

## **5.1 Business Test Cases**

| \# | Test Case | Acceptance Criteria |
| :---- | :---- | :---- |
| 1 | Type "record" and press Enter | Recording starts within 2s; status dot turns red; timeline animates. |
| 2 | Click ● Record button | Same as test 1\. |
| 3 | Type "stop" while recording | Recording stops; file saved to Desktop; dialog appears. |
| 4 | Click ■ Stop while recording | Same as test 3\. |
| 5 | Press Enter with empty input | Nothing happens; input is focused. |
| 6 | Toggle Mic button | Button turns red-tinted; mic is passed to ffmpeg on next recording. |
| 7 | Toggle System audio off | Button loses blue tint; audio flag removed from next recording. |
| 8 | Click a window in sidebar | Item highlights with checkmark; previously selected item deselects. |
| 9 | Recording with no ffmpeg | Error dialog shown within 2s: "ffmpeg not found." |
| 10 | Close app while recording | Recording stops cleanly; no orphan ffmpeg process remains. |

# **6\. Release Plan**

| Milestone | Target date | Scope |
| :---- | :---- | :---- |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |

# **7\. Open Questions**

| \# | Question | Owner | Status |
| :---- | :---- | :---- | :---- |
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |
|  |  |  |  |

# **8\. Success Metrics**

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAANsAAACcCAYAAAD23t6UAAATyElEQVR4Xu2d+XcVVbbH/Uf6vZ/eej4ZTIsMMibMECCEhAhhDvMgghBGQWxUkBkhMuoD3gPERsV2QAVElFZUuhEa7F4+QAZRkDlgwuh52Yd1KufuqntT59wa4Oa71/qsOsM+Z9e9tb+36ia3Tj308COPCQBA+DzEGwAA4QCxARAREBsAEfHQH/79PwQAIHwgNgAiAmIDICJcYstq0Fy0yO4CAAgIT7FxJwBAMEBsAEQExAZARCQVW03GJwIApAZiAyAikoptwaIyl7PCr9iUPfX0FFdfKsg+3L5TLCtb6zuWGsf99TavfgCiIhKxlZdfc/WlgozERmUToSprmdNV1mfOmuO0Ub1dhwLRo3CAaxwAURCa2FauXuckuu5PNqBktFNWfdxIbIuXrpBl6n9l+eqE/mvXrrtiKjv+40mnfvPmTblNFm/Hzs/kdtKUWeLChUtOO9nSZaucfVDGYwLgF19iO3b8RELCeRmfmOz3338Xr6/bmNBPlkxsBw8dET2fLJFlLjbdl/ZNlXlMZa3b5cvtl199K7d8jsrKSqeu2vSy6lf7QGfnwqJBrpgA+CWp2ExNn3Tk6Im8W/zj8D+debnYhg4fJ7edu/Zy2lOJTdX5iyGb8/ISuaUzH9lX+/Y7vsqoTJeaynbu2pP0Nev7AEA6JBWbzra/bHe16fBkVKbqX3/zN6dOVlFRKebOW5rgR0ZnwqPHfpRlLjbqI5u3YJm4dPmK087j6vG/2Lsvqdi46W19+g2XHxh0iQmxgaCIRGwFRQNlfdPmreLW7dtOvzJ9jDIuNu5DQkq2H6dO/yTLHXOLPMVW1Huw3P505heRl99Xln89f0HMmj3P8SH7ct+3rn0AwJZQxAYAcAOxARARvsS2ecvbzqVVMuNjAACJ+BIbACB9IDYAIgJiAyAiPMXGl98CAKQHxAZAREBsAEQExAZAREBsAEQExAaABS/Nmetqq4lYxDZ33iL5i5OTJ085bY2aZMtf9Z89e050yu2R0P5LVRtvD4ur5eVy39a+tt7VBx5sunQrEGVlZWLS5Gli1apVrn5qGzlqrOxfvHiJq5/70ra4z0BROmmqGPPUONnmNa/CSmxt23cRTZu3ERNKp8n6pCkzxJRpzzn9w0Y8JUaOHufUu3UvEktfWSH+2KCZGD7yabH5ja1OH1mdeo/LLY+j+hs2bpnQps83YtS4qvENxcvz7705NH/f/kMc3yZNc8TsF1926gNLRsjxk6fO9IzF2/TX8l91GogBg4aL52fPEU80ay3b6J65Vatfr9rHVqJkyEhnHO0XbVvldBT9BgwVjZ/IlvUlr7zqigGiQRcCCYqOp6p37pKf0O8lGhKqEpQuNsqxVOMUVmL7301b5Fno1q1bMkHf/csH4u7du6J+VhPxyrKV8oxFSxHQnc7kr3xInMeO/5gwF83x3PMvSp/WbXNdscj2/vUrV5uaT9lne/ZWfXIVivPnL8j6zl2fyTrZJzs+lXU19uLFS+LOnbuiTbvE17n9ox2u+PprIYGRffTxTrlt1qKt3O75/K/yrEum76Panjv3q/OB8s629+R7x+OA8NGF0LOoT9UHYQen3n/gkBrFptry8osSxDZ4yAhRWDXfwoWLPMcprMWmynqCDRk2puqM11Z8te8b50ZP/SxGkLj0+okTJ8W69RtleeWq1+SY3K6FCT45bTo77Xw+PT7Z7du3q4R0R5aVURsZ95+/cKlTJjHodYX+WpTY1NgzZ36uEuGNqgM1zDW3Kn+7/+9yS/tNpu8LiBZdCD0Ke1flVSenPrBkWEqxFfQsFh065bn69TNbt+49XeN0Ahcb2TMTpzqf5Bv+Z3PCWDoLZD32RML4wUNHJ/h8sfdLV0zVzufT4+tlVR86fIyrTZW5uK5f/y2hTmcw/bXoYitbsUb839FjnmJ7pG71ZTGdgWm7fsMmcfDQ4YT5QbToQnh63ARR79HGTj23a4+UYiMhkQ/v55eR9IeTR+pWX57qhCI2uqRUpnzIlpXd20EydfZZtea/nbYrV67KLZ3J9Pnpkk9vV0bzkSnfBg2bO31kvM73l4uNLnGV7f/bAbFm7bqE16LE9ttvv8ktfVf8cPsnsjx2XKnjp4zmVGLT91v1gWihy7958xeI4r6DPIVF2655hbJ/5cqVrvHU/3ijFmLa9BkJYutdRafcfDFj5iyXSHWsxFZb0c9s4MGlflb1GY1o1KSVUyYx8X6dltnV3/NMgdgMgNhAOkBsAEQExAZAREBsAEQExAZARBiLrWHj1rLfFhrP5ySySh4GGcyogj/EzjP/9p+RwfPbWGx16zd2iceGOvUauebmBwdkFjzx44ALIkx4fhuLrUV2rks4drh/A8kPDsgseOLHARdEmPD8thAbF00iV6+Wy98RXr58xdXH4XPzgwMyC574ccAFESY8vwMXGwlNwfs4fG5+cEBmwRM/DrggwoTnd+BiS+fMBkCmQ3kfmNhM4HPzT0KQWfCzTBzws0+Y8PwOXGz0CNyKykpfD4jnc/ODAzILnvhxwAURJjy/AxcbvrOBZPDEjwMuiDDh+Q2xgcjgiR8HXBBhwvM7cLHRo3xxGQm84IkfB1wQYcLzO3CxmcDntr1PzHYcxkYH4t6D8j4wsaXzp/9kO1gTtuMwNjoQ9x6U94GJLZ3vbABkOpT3gYnN9sxG603SwjpUVitZ/XnrNld8zvJXV8tFggiq6+WaUL5vbHlLxqSyn5gKWplJ7bNJXOLI9/9yVu0yiUuLw5KtXrtO1v3GrVu/kfjhh6MSWjTW5D2mhWdv3Lgp3tn2vqzr7xv39eLAgYNyzU1a2dokLjF+whSnbBqX+Pqb/XJrGpewiUf+5eXXXO0KynsDsYXzQ2QyVSah0vbq1ZqTaPdnnyedpyZ4zIKefXzFVKhVt/hcfiCb9uws47hqdTL6QFPzcB8v6IOhfcc8uZK1+jCkdj9x33r7Xbm1ea2U5MNHjhXde/SSK5KZxH3v/e3iwsWLTt0krvI/euy4LJvE1cfztlTQBxodS1poWK1+zaHc9y02ujXGLRxz9FtsaAeV0XLQ6kXSQeLxOfRJQkYrDlNdGffzQtmYsROcMX5iEqPGjJdLn6txyrifF2Slk5+VYjONq8ZfuHAvCU3iqkViC4v6WsdVWzJ637hPMmj9TboKsYmrsImrxGYT1zTen2ZXP2hDLTrModz3LTYiqJtH6dOO1tundfd37Nwt21RCUFldKnlB4/S1+re8mXiqX7homWuMPlZ/FoAyKqeKqcYSuqk1/wk/cbmZxFV1WvBV768prl73G1cdHzWG93u16aixr72+oeqM2jVhjN+4XviNS3CxpYqrj+f5wX286Degegwtp8/7Ccp/I7GFAdnx4ydE85bt5BLkdG3t50XSpdyuT/dI355P9pNLhVdUVMjvgNyXo3zp+xPF/PmXs75i6tjEJdSZzTQurb5Mzy0wjfvqirXyA42ecXDoH0eM3mOyw4e/r7pk/0J+z9TfN+7LmfHcC3I8jSVM4nJM4iqU2Gzi2sSjY8mfZaFzX4gNgNqAsdiCuowEoLZB+e9bbGGuQQJApkO571tsYf3pH4DaAOW+gdi4aOzhcwOQ6VDeByK2ASWjPX+mRU/t5G3J5gcgk6G8T1tsnbo8mfQ3kdS2cfNWVzufG4BMJxCx8R8gX7p0WVy7fl2W5y9cLttb5nSF2ECtxlpsn+/dlyAyXWyt2+XL8rKytY4YP9mx21psfUvGu9rS7fPTb+pn6x8WcexHHDEfFKzFxkWmi03103/UVfns2V8htoiJYz/iiBkm9HNC9UjqmuzkqdPSn8+hgNg82jl+/Wz9wyKO/YgjZljY2sZNb7rmIqzFtuvTz11CU2LDZaSZf1jEsR9xxAyLdIzPRViLTYeLzc8fSLIL1oi8Ud8BcN+SjnHtBCY2mz/9Q2zgficd49oJTGzEgEHm/9SG4MD9TDrGtROo2Ezhc6ci1fcA2z4//aZ+tv5hEcd+xBEzLGwtoD+QxPND5FQH0LbPT7+pn61/WMSxH3HEDAu6KZeu1kyM/Pk8Csp932ILYw0SP6Q6gLZ9fvpN/Wz9wyKO/Ygj5oMC5b5vsRG4eRQAOyj/jcQGALADYgMgIiA2ACIiqdgAAMHjKTauSgBAekBsAEQExAZAREBsAEQExAZAREBsoFYxYeJkMfuFl0STpjmuPmLBwkWyn7dzVq2696y8Dp3yxLTpMyWDh4yQjz3jvgorsfUbMFQcOfLPhLYzZ36WWzLuz32I8+cvuPoBCJMu3QpEWVmZmDR5miMWHWobOWqs7F+8eImrn/vStrjPQFE6aaoY89Q42eY1r8JKbOOemZwgqmvXrjv1EaPGOe30iNip02c59bNnz8lt2Yo10j8vv5es01MblU9Rr/7y00HN03/gMNGuQzfXPgBgii4EEpR+FurcJT+h30s0JFQlKF1s+lnSa5zCWmzvf/CxUyc7efKUU6YtPTuNnqV86vRPsj50+BjRKbeH4zNvwVJxtbxc1nsUFousx5rKsvJX85DpYgTAFl0IPYv6iFY5HZx6/4FDahSbasvLL0oQG10+FlbNt7DqEtRrnMJabLSlh3XXqddQvPDSPJfY1Fah18m2vfuB0+YlNj4GgHTRhdCjsLfIadPJqQ8sGZZSbAU9i+X3M96vn9m6de/pGqeTltiUUTmV2OjJj+o72gcfVp8Re/cZJJ9ZnNu10LlsVOPoKZdr1q4TBw8ddsUHwIaVK1c6Zf6drFGTVinFlt26oxg8dKSrn19G0rzJ/kiSltje2PJWUrGph8srU4tXqn4FXW6q9jt37sptnXqPO35k+jOOAbCFLv/mzV8givsO8hQWbbvmFcp+XZi63+ONWohp02ckiK13FZ1y88WMmbNcItWxEhsADzL1sxon1OmspsokJt6v0zK7+nueKRAbABEBsQEQERAbABEBsQEQERAbABFhLLaglrLLKnnYgerFxcUggyktLY2dnJycyOC6MRZb3fqNXeKxgRZphdhqFzzx44ALIky4dozFFuTy4xBb7YInfhxwQYQJ146F2LhoErl6tVyudX758hVXHwdiq13wxI8DLogw4doJXGz8oYipgNhqFzzx44ALIky4dgIXm8mZjc/NfzPpF9txGBsdiHsPyvvAxGYCnzvZDtaE7TiMjQ7EvQflfWBiKywaJCoqK0WPwgGuPg6fG4BMh/I+MLGZfGfT56WHzqlbbdTtNX/eus0Vn7P81dXyVh6C6nq5JpQv3SZEMansJ6ai3qONnX02iUsc+f5f8n4907jPz54j35vVa9fJut+4dKf7Dz8clbTK6Wj0HtPSFjdu3BTvbHtf1vX3jft6ceDAQXnHfqMm2UZxifETpjhl07jE19/sl1vTuIRNPPKnG6p5u4LyPlax0Y12ZKquyn7emO++O5RQr6y84fJJhu5rElMfo8aZxG3QsLn4ZMcuMe3ZWVZxCbrvj7YmcQmKTc84t4l76dJleTe9aUyF/n75ibtoSZlo37H6zmjTuCdOnBRHjx2XZZO4CtN4dCO0Kk+cNN3VT1DeBya2gqKBxpeRBT37OAdCF97wkWNd8Tn0SUJ27tyvsq6M+3mhjO4UV2P8xCRGjRkv/tigmTNOGffzgqx08rMJYvMbV42/cOGiU/Ybd/MbW6VvYVFf67hqS0bvG/dJxkcf75RXITZxFTZxudhM4prG+9PsuU553fqNrn6C8j4wsZnQvUcvMXnqTHkH946du+X8KiGorC6VvKBxhKpveTPxVL9w0TLXGH2sfue3MiqniqnGEro90az6Sap+4nIziavq6zdsSuivKa5e9xtXHR81hvd7temosa+9vkG0bd81YYzfuF74jUtwsaWKq4/n+cF9vOg3oHrMc8+/6OonKO8DE5vtn/4XLl7uvKhH6t67vv509x5XfM63+/8ufd/Z9p5o3TZXXl7R9wvu54Xybd6ynYxZUVHhK6YOmWlcYuy4UjGhdJpx3NOnz8iYdBlqEnfM2Ily3O3bt+Wlmcl7rBstQai/b9yX89LcBQnjTeJyTOIq6LsxbW3i2sSjY3nr1i1Xu4LyPjCx2XxnA6C2QHkfmNhsz2wA1AYo732LrWnzji7R2EDz8LkByHQo932LjW6N4cKxgebhcwOQ6VDu+xYbEdTNowDUNij/jcQGALADYgMgIozFxi8LbeBzAlAboNz3LbYg1yDhcwOQ6VDu+xZbkGuQ8LkByHQo9w3ExkVjD58bgEyH8j4QseU1aye2PZrlak8GnxuATIfyPm2xLctqKIUGsQGQHMr7tMWmhAaxAZAcynsrsc3PapwgMl1sG7Mek+WSRtlyS/V0xNa3ZLyrLd0+P/2mfrb+YRHHfsQR80HBWmxcZPzM5tUGsUVLHPsRR8wwoZub79y5o9+Wl9ROnjrtPM7aC4jNo53j18/WPyzi2I84YoaFrW3c9KZrLsJabB1adHQJTQmLLhvfzrpXpm2yy8jsgjUib9R3ANyXpGNcO2mJTYeLzQ8QGrjfSce4dgITW5uWnSE2kHGkY1w7gYmNyGvW3khsNB8EB+5n0jGunUDFZgqfOxWpvnTb9vnpN/Wz9Q+LOPYjjphhYWuB/IEkrjVIUh1A2z4//aZ+tv5hEcd+xBEzTGL7039ca5CkOoC2fX76Tf1s/cMijv2II+aDAuW+b7ERWIMEADso/43EBgCwA2IDICIgNgAiIqnYAADB4yk2vQ4ASB+IDYCIgNgAiAiIDYCIgNgAiAiIDYCIgNgAiAiIDYCIgNgAiAiIDYCIULr6f/GwTLSzKclYAAAAAElFTkSuQmCC>