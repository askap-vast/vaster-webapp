// const canvas = document.getElementById('gifCanvas');
// const ctx = canvas.getContext('2d');

// let gif = new Image();
// gif.src = 'your-gif-file.gif'; // replace with the path to your GIF file

// let gifFrames = [];
// let currentFrame = 0;
// let playing = false;
// let gifWidth, gifHeight;
// let frameDuration = 100; // adjust this for your GIF's frame rate

// gif.onload = function() {
//     gifWidth = gif.width;
//     gifHeight = gif.height;
//     canvas.width = gifWidth;
//     canvas.height = gifHeight;

//     extractFrames(gif.src, function(frames) {
//         gifFrames = frames;
//         drawFrame(0);
//     });
// };

// // on page load, run the init

// function extractFrames(src, callback) {
//     const frameCanvas = document.createElement('canvas');
//     const frameCtx = frameCanvas.getContext('2d');

//     let img = new Image();
//     img.src = src;
//     img.onload = function() {
//         frameCanvas.width = img.width;
//         frameCanvas.height = img.height;
//         frameCtx.drawImage(img, 0, 0);

//         // simulate extracting frames, assuming 10 frames for simplicity
//         const frames = [];
//         for (let i = 0; i < 10; i++) {
//             frames.push(frameCtx.getImageData(0, 0, img.width, img.height));
//         }
//         callback(frames);
//     };
// }

// function drawFrame(frameIndex) {
//     ctx.putImageData(gifFrames[frameIndex], 0, 0);
// }

// function playGif() {
//     if (!playing) {
//         playing = true;
//         play();
//     }
// }

// function play() {
//     if (playing) {
//         drawFrame(currentFrame);
//         currentFrame = (currentFrame + 1) % gifFrames.length;
//         setTimeout(play, frameDuration);
//     }
// }

// function pauseGif() {
//     playing = false;
// }

// function prevFrame() {
//     currentFrame = (currentFrame - 1 + gifFrames.length) % gifFrames.length;
//     drawFrame(currentFrame);
// }

// function nextFrame() {
//     currentFrame = (currentFrame + 1) % gifFrames.length;
//     drawFrame(currentFrame);
// }
