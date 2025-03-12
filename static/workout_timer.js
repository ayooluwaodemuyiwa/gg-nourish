document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const timerElement = document.getElementById('timer');
    const progressElement = document.getElementById('progress');
    const startBtn = document.getElementById('startBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const skipBtn = document.getElementById('skipBtn');
    const closeBtn = document.getElementById('closeBtn');
    const doneBtn = document.getElementById('doneBtn');
    const completionScreen = document.getElementById('completionScreen');
    const completionTimeElement = document.getElementById('completionTime');
    const workoutNameElement = document.getElementById('workoutName');
    const workoutDescriptionElement = document.getElementById('workoutDescription');
    const currentExerciseNameElement = document.getElementById('exerciseName');
    const currentExerciseDurationElement = document.getElementById('exerciseDuration');
    const currentExerciseDescriptionElement = document.getElementById('exerciseDescription');
    const currentExerciseBenefitElement = document.getElementById('exerciseBenefit');
    const exerciseListElement = document.getElementById('exerciseList');

    // Timer variables
    let timerInterval;
    let totalWorkoutTime = 0; // in seconds
    let currentTime = 0;
    let isRunning = false;
    let currentExerciseIndex = 0;
    let exercises = [];
    let totalExerciseTime = 0;
    let elapsedTime = 0;

    // Get workout data from URL parameters or use default
    function getWorkoutData() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const workoutData = urlParams.get('workout');
            
            if (workoutData) {
                return JSON.parse(decodeURIComponent(workoutData));
            } else {
                return getDefaultWorkout();
            }
        } catch (error) {
            console.error('Error parsing workout data:', error);
            return getDefaultWorkout();
        }
    }

    // Default workout if none is provided
    function getDefaultWorkout() {
        return {
            break_name: "10-Minute Gaming Break",
            exercises: [
                {
                    name: "Neck Stretches",
                    duration: "60 seconds",
                    description: "Gently tilt your head side to side and front to back",
                    benefit: "Relieves neck tension from looking at the screen"
                },
                {
                    name: "Wrist Rotations",
                    duration: "60 seconds",
                    description: "Rotate your wrists in circles in both directions",
                    benefit: "Prevents wrist strain from keyboard and mouse use"
                },
                {
                    name: "Shoulder Rolls",
                    duration: "60 seconds",
                    description: "Roll your shoulders forward and backward",
                    benefit: "Releases shoulder tension"
                },
                {
                    name: "Stand and Stretch",
                    duration: "120 seconds",
                    description: "Stand up, reach for the ceiling, then touch your toes",
                    benefit: "Improves circulation and stretches the whole body"
                },
                {
                    name: "Quick Walk",
                    duration: "180 seconds",
                    description: "Walk around your room or to the kitchen and back",
                    benefit: "Gets your blood flowing and gives your eyes a break"
                },
                {
                    name: "Deep Breathing",
                    duration: "60 seconds",
                    description: "Take 6 deep breaths, inhaling for 4 counts and exhaling for 6 counts",
                    benefit: "Reduces stress and increases oxygen flow"
                }
            ],
            total_time: "10 minutes",
            response: "Time for a quick break! This 10-minute routine will help you feel refreshed and ready to get back to gaming with better focus."
        };
    }

    // Initialize the workout
    function initializeWorkout() {
        const workout = getWorkoutData();
        
        // Set workout details
        workoutNameElement.textContent = workout.break_name;
        workoutDescriptionElement.textContent = workout.response;
        
        // Process exercises
        exercises = workout.exercises.map(exercise => {
            // Convert duration string to seconds
            const durationMatch = exercise.duration.match(/(\d+)/);
            const durationSeconds = durationMatch ? parseInt(durationMatch[0]) : 60;
            
            return {
                ...exercise,
                durationSeconds
            };
        });
        
        // Calculate total workout time
        totalExerciseTime = exercises.reduce((total, exercise) => total + exercise.durationSeconds, 0);
        totalWorkoutTime = totalExerciseTime;
        currentTime = totalWorkoutTime;
        
        // Update timer display
        updateTimerDisplay();
        
        // Set up exercise list
        setupExerciseList();
        
        // Set up current exercise
        updateCurrentExercise();
    }

    // Format time in MM:SS
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // Update the timer display
    function updateTimerDisplay() {
        timerElement.textContent = formatTime(currentTime);
        const progressPercentage = ((totalWorkoutTime - currentTime) / totalWorkoutTime) * 100;
        progressElement.style.width = `${progressPercentage}%`;
    }

    // Set up the exercise list
    function setupExerciseList() {
        exerciseListElement.innerHTML = '';
        
        exercises.forEach((exercise, index) => {
            if (index === 0) return; // Skip the first exercise as it's shown in current exercise
            
            const exerciseCard = document.createElement('div');
            exerciseCard.className = 'exercise-card';
            exerciseCard.dataset.index = index;
            
            exerciseCard.innerHTML = `
                <div class="exercise-header">
                    <h4>${exercise.name}</h4>
                    <span>${exercise.duration}</span>
                </div>
                <p>${exercise.description}</p>
                <p class="benefit"><span>Benefit:</span> <span>${exercise.benefit}</span></p>
            `;
            
            exerciseListElement.appendChild(exerciseCard);
        });
    }

    // Update the current exercise display
    function updateCurrentExercise() {
        if (currentExerciseIndex >= exercises.length) {
            // Workout completed
            completeWorkout();
            return;
        }
        
        const exercise = exercises[currentExerciseIndex];
        
        currentExerciseNameElement.textContent = exercise.name;
        currentExerciseDurationElement.textContent = exercise.duration;
        currentExerciseDescriptionElement.textContent = exercise.description;
        currentExerciseBenefitElement.textContent = exercise.benefit;
        
        // Highlight current exercise in the list
        const exerciseCards = exerciseListElement.querySelectorAll('.exercise-card');
        exerciseCards.forEach(card => {
            card.classList.remove('active');
            if (parseInt(card.dataset.index) === currentExerciseIndex) {
                card.classList.add('active');
            }
        });
        
        // Update the current exercise card
        document.getElementById('currentExercise').className = 'exercise-card active';
    }

    // Start the timer
    function startTimer() {
        if (isRunning) return;
        
        isRunning = true;
        timerElement.classList.add('active');
        startBtn.disabled = true;
        pauseBtn.disabled = false;
        
        timerInterval = setInterval(() => {
            currentTime--;
            elapsedTime++;
            updateTimerDisplay();
            
            // Check if current exercise is complete
            const currentExercise = exercises[currentExerciseIndex];
            const exerciseElapsedTime = elapsedTime - (totalExerciseTime - currentExercise.durationSeconds - 
                exercises.slice(0, currentExerciseIndex).reduce((total, ex) => total + ex.durationSeconds, 0));
            
            if (exerciseElapsedTime >= currentExercise.durationSeconds) {
                // Move to next exercise
                currentExerciseIndex++;
                updateCurrentExercise();
            }
            
            if (currentTime <= 0) {
                completeWorkout();
            }
        }, 1000);
    }

    // Pause the timer
    function pauseTimer() {
        if (!isRunning) return;
        
        isRunning = false;
        timerElement.classList.remove('active');
        clearInterval(timerInterval);
        startBtn.disabled = false;
        pauseBtn.disabled = true;
    }

    // Skip to the next exercise
    function skipExercise() {
        if (currentExerciseIndex >= exercises.length - 1) {
            completeWorkout();
            return;
        }
        
        // Adjust timer
        const currentExercise = exercises[currentExerciseIndex];
        const remainingExerciseTime = currentExercise.durationSeconds - 
            (elapsedTime - (totalExerciseTime - currentExercise.durationSeconds - 
            exercises.slice(0, currentExerciseIndex).reduce((total, ex) => total + ex.durationSeconds, 0)));
        
        currentTime -= remainingExerciseTime;
        elapsedTime += remainingExerciseTime;
        
        // Move to next exercise
        currentExerciseIndex++;
        updateCurrentExercise();
        updateTimerDisplay();
    }

    // Complete the workout
    function completeWorkout() {
        pauseTimer();
        
        // Calculate actual time taken
        const minutesTaken = Math.ceil(elapsedTime / 60);
        completionTimeElement.textContent = minutesTaken;
        
        // Show completion screen
        completionScreen.classList.add('show');
        
        // Send message to parent window
        try {
            window.opener.postMessage({ type: 'workout_completed' }, '*');
        } catch (error) {
            console.error('Error sending message to parent window:', error);
        }
    }

    // Close the window
    function closeWindow() {
        try {
            window.opener.postMessage({ type: 'workout_closed' }, '*');
        } catch (error) {
            console.error('Error sending message to parent window:', error);
        }
        window.close();
    }

    // Event listeners
    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    skipBtn.addEventListener('click', skipExercise);
    closeBtn.addEventListener('click', closeWindow);
    doneBtn.addEventListener('click', closeWindow);

    // Initialize
    initializeWorkout();
});
