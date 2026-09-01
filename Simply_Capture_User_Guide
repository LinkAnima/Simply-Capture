# Simply Capture: User Guide & Best Practices

**Simply Capture** is a camera setup assistant designed to bridge the gap between real-world cinematography and 3D animation. It allows you to quickly configure Maya’s camera with familiar photographic terminology (f-stops, shutter speeds, focal lengths) while ensuring your scene units and calculations remain accurate.

This guide covers how to use the tool effectively, from basic setup to advanced focus pulling.

---

## 1. The Core Philosophy: "Why Use This Tool?"

In Maya, camera settings are often hidden in complex attribute editors or require manual calculation. Simply Capture brings these settings to a single, intuitive interface.

*   **Photographer, not Coder:** You think in *mm* (lenses) and *f-stops* (aperture), not inches and radians. The tool handles the conversion.
*   **Unit-Safe:** You set focus in **Meters** (human scale), but the tool automatically converts to your scene’s current units (CM, MM, Inches, Feet) to avoid scaling errors.
*   **Workflow Acceleration:** Stop typing numbers into attribute editors. Pick a preset, check a box, and hit **Apply**.

---

## 2. Interface Overview

The window is divided into five logical sections:

1.  **Camera Selection:** Choose which camera to control.
2.  **Lens & Sensor:** Define the "Optics" (Focal Length) and "Film Back" (Sensor Size).
3.  **Exposure & Motion:** Set Aperture (Depth of Field) and Shutter Speed (Motion Blur).
4.  **Focus Control:** Manual focus, auto-focus from selection, or rack-focus automation.
5.  **Action Buttons:** Apply, Reset, or Close.

---

## 3. Feature-by-Feature Guide

### A. Camera Selection (Top Section)

*   **Select:** A dropdown listing all perspective cameras in your scene.
    *   *Tip:* If you have multiple cameras named `camera`, the tool adds a number suffix (e.g., `camera1`, `camera2`) to help you distinguish them.
*   **Refresh:** Click this if you add a new camera to the scene or if the dropdown looks outdated.
*   **Load:** Click this to **pull the current values** from the selected camera into the UI.
    *   *Use Case:* You opened an old scene or a colleague’s file. Hit "Load" to see what lens and aperture they used.

### B. Lens & Sensor (The "Look")

This section defines the geometry of your shot.

#### 1. Focal Length (Lens Preset)
*   **Dropdown:** Choose a standard lens (e.g., `24mm Wide`, `50mm Normal`, `85mm Portrait`).
*   **Slider:** You can manually adjust the focal length in **millimeters**.
*   **FOV Display:** The text next to the slider updates in real-time to show the **Horizontal and Vertical Field of View** in degrees.
    *   *Best Practice:* Use the presets for consistency across your team. If you need a non-standard focal length (e.g., 52mm), type it in; the preset will automatically switch to "Custom."

#### 2. Sensor / Film Back (Preset)
*   **Dropdown:** Select your sensor size (e.g., `Full Frame 35mm`, `Super 8mm`, `65mm VistaVision`).
*   **H / V Fields:** You can manually override the horizontal and vertical sensor dimensions in **mm**.
*   *Note:* Changing the sensor size changes the Field of View. A 50mm lens on a `Super 8mm` sensor looks much wider than on a `Full Frame 35mm` sensor.

### C. Exposure & Motion (The "Feel")

#### 1. Aperture (Depth of Field)
*   **Slider:** Set the f-stop (e.g., f/2.8, f/11).
    *   **Low f-stop (1.4 - 2.8):** Shallow depth of field (blurry background).
    *   **High f-stop (8 - 16):** Deep depth of field (everything sharp).
*   **Enable Depth of Field:** **Check this box** to actually activate the DOF blur in your render/view. If unchecked, the f-stop value is saved but won’t blur the background.

#### 2. Shutter Speed (Motion Blur)
*   **Dropdown:** Choose a standard shutter speed (e.g., `1/48`, `1/120`).
*   **Angle Display:** Shows the resulting shutter angle in degrees.
*   **Motion Blur Preview Bar:** A visual indicator of how much blur will occur.
    *   **The "180-Degree Rule":** For standard cinematic look, keep the angle at **180°**.
    *   **Custom:** If you type a custom speed (e.g., 1/33), the dropdown switches to "Custom," and the angle updates.

### D. Focus Control (The "Sharpness")

This is the most critical part of cinematography.

#### 1. Manual Focus
*   **Slider:** Drag to set the focus distance in **Meters**.
*   **Infinity:** Check this box to focus at infinity (background becomes sharp, foreground blurs). The slider disables itself.
*   **Focus Offset:** A small slider to nudge the focus slightly closer or further than the calculated point. Useful for fine-tuning "breathing" or artistic focus shifts.

#### 2. Smart Focus Button ("Focus")
Clicking the **Focus** button calculates distance based on your selection:
*   **BBox Center (Default):** Calculates the center of the bounding box of your selected object(s).
*   **Pivot:** Uses the object’s pivot point.
*   **Use Focus Target:**
    1.  Select an object in the viewport.
    2.  Click **Set** next to "Focus Target."
    3.  Check **Use Focus Target**.
    4.  Now, clicking **Focus** will *always* focus on that specific object, regardless of what else you select. *Great for complex assemblies where the BBox center might be in empty space.*

### E. Focus Pull Assistant (Animation)

For animating a rack focus (shift from foreground to background).

1.  **Set Target A:** Select the object you want to start sharp. Click **Set A**.
2.  **Set Target B:** Select the object you want to end sharp. Click **Set B**.
3.  **Timing:**
    *   **Start:** The frame where Target A is sharp.
    *   **End:** The frame where Target B is sharp.
4.  **Curve:**
    *   **Smooth (Recommended):** Natural, cinematic ease.
    *   **Linear:** Mechanical, robotic shift.
    *   **Ease In/Out:** Specific timing flavors.
5.  **Create Focus Pull:** Click this button. It will automatically:
    *   Set keyframes on `focusDistance` at the Start and End frames.
    *   Apply the chosen interpolation curve.
    *   *Tip:* You can still animate the camera *movement* separately. This tool only handles the *focus* animation.

---

## 4. Best Practices & Pro Tips

### 🎬 Cinematic Consistency
*   **The 180-Degree Shutter:** Unless you are going for a specific artistic look (e.g., fast 90° for crisp action, or 360° for slow motion), keep your shutter angle at **180°**. This is the industry standard for motion blur.
*   **Standard Lenses:** Stick to the presets (`24mm`, `50mm`, `85mm`). These are the "workhorse" lenses. Using odd numbers like `53.2mm` can make it harder for your team to understand the shot design.

### 📏 Unit Safety
*   **Always check the FOV Display.** When you change the Sensor Preset, the FOV changes. If you switch from `Full Frame` to `Super 8`, your `50mm` lens becomes a wide-angle. Watch the numbers.
*   **Focus in Meters:** The UI uses meters for focus because it’s intuitive. However, if your scene is in **Inches** or **Millimeters**, the tool automatically converts. *Never worry about unit mismatches.*

### 🎥 Focus Pulling Workflows
*   **Static Shot:** Use **Manual Focus**. Set the slider, check DOF, and be done.
*   **Travelling Shot (Crane/Dolly):** Use **Focus Pull Assistant**. If your camera moves closer to a subject, a static focus will go blurry. The Assistant creates the keyframes to keep the subject sharp as the camera moves.
*   **Multi-Object Shots:** Use **Focus Target**. If you have a character with a complex rig, the "BBox Center" might focus on a hat or a sword hilt instead of the eyes. Set a specific mesh or joint as the "Target" for precise focus.

### 🚀 Workflow Efficiency
1.  **Start Every Scene with "Load":** If you are opening a file, hit **Load** first to see the previous camera settings.
2.  **Save Presets in Your Head:**
    *   *Interview:* 50mm, f/2.8, 180° Shutter.
    *   *Establishing:* 24mm, f/8, 180° Shutter.
    *   *Close-Up:* 85mm, f/1.4, 180° Shutter.
3.  **Use "Reset" for Quick Changes:** If you start messing with numbers and want to go back to a standard 50mm/f/2.8/180° look, hit **Reset**. It clears all your custom adjustments back to the defaults.

### ⚠️ Troubleshooting

*   **"No Perspective Cameras" message:** Make sure you have a camera that is *not* orthographic (top/side/front). The tool only works on perspective cameras.
*   **Focus looks wrong:** Check if **Depth of Field** is enabled. If the box is unchecked, the f-stop doesn’t matter. Also, ensure your **Focus Distance** is actually correct (try the "Focus" button to verify).
*   **Motion Blur is too strong/weak:** Check the **Shutter Angle**. If it’s 360°, your blur will be very heavy. If it’s 90°, it will be very crisp.
*   **Sensor dimensions look weird:** If you manually typed in sensor dimensions, remember that Maya’s `filmAperture` is in **inches**. The tool converts for you, but if you bypass the tool and type into the Attribute Editor, use inches. In Simply Capture, always use **mm**.

---

## 5. Quick-Reference Cheat Sheet

| Goal | What to Do |
| :--- | :--- |
| **Standard Cinematic Look** | Lens: `50mm`, Aperture: `f/2.8` + `DOF ON`, Shutter: `1/48` (180°) |
| **Wide Establishing Shot** | Lens: `24mm`, Aperture: `f/8` (Deep DOF), Shutter: `1/48` |
| **Dreamy/Blurred BG** | Lens: `85mm` or `135mm`, Aperture: `f/1.4` - `f/2.8` + `DOF ON` |
| **Action/Crisp Motion** | Shutter: `1/120` or `1/240` (90° or lower angle) |
| **Slow Motion Look** | Shutter: `1/24` or `1/12` (360° or higher angle) |
| **Rack Focus Animation** | Use **Focus Pull Assistant**: Set Target A, Set Target B, Define Frames, Click Create. |
| **Verify Settings** | Click **Load** to see what’s currently applied to the camera. |

---

## 6. Final Thought

**Simply Capture** is not just a tool; it’s a mindset. It forces you to think about your camera like a cinematographer, not just an animator. Use it to enforce consistency across your team, to quickly test "looks" without breaking your scene units, and to automate the tedious parts of focus pulling.

*Happy Shooting!* 🎥
