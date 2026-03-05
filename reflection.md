# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the secret number kept changing" or "the hints were backwards").

---When I first ran the game, it mostly worked but the behavior felt inconsistent. The hints for "Too High" and "Too Low" sometimes did not match the number I guessed. Another problem was that the difficulty settings did not always match the number range being used in the game. I also noticed that the secret number could behave strangely during guesses, which made the hints unreliable. These issues made it clear that there were logic bugs in the code.

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion that was incorrect or misleading (including what the AI suggested and how you verified the result).

---I used ChatGPT and GitHub Copilot to help analyze and debug the code. One correct suggestion from AI was that the secret number was sometimes being treated as a string instead of an integer, which caused incorrect comparisons when checking guesses. I verified this by reading the code and testing the game, and once I removed the string conversion the hints behaved correctly. One misleading suggestion from AI was to add more exception handling around the guess comparison logic. While this prevented errors from appearing, it did not solve the actual problem because the real issue was inconsistent data types. I confirmed this by testing the game again and seeing that the bug still existed until the comparison logic was fixed.

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

---To determine whether a bug was fixed, I tested the game both manually and with small test cases. For example, I tested guessing numbers higher and lower than the secret number to confirm that the correct hint was displayed each time. I also ran the game multiple times with different difficulty levels to verify that the number range matched the difficulty setting. AI helped suggest a simple pytest test that checked whether a guess greater than the secret returned the "Too High" outcome. Running these tests helped confirm that the comparison logic was working correctly.

## 4. What did you learn about Streamlit and state?

- In your own words, explain why the secret number kept changing in the original app.
- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?
- What change did you make that finally gave the game a stable secret number?

---The secret number kept changing in the original app because Streamlit reruns the entire script every time a user interacts with the interface. If the secret number is generated normally in the script, it gets regenerated on every rerun. Session state solves this problem by storing values that persist between reruns of the app. I would explain Streamlit reruns to a friend as the app restarting its script every time you click a button or enter input. The change that fixed the issue was storing the secret number inside st.session_state so it would stay the same during the game.

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

--One habit I want to keep using is adding comments like FIXME and FIX while debugging so I can clearly track where problems exist and how they were repaired. Next time I work with AI on a coding task, I would break the problem into smaller parts and verify each suggestion before applying it to the code. This project showed me that AI generated code can look correct but still contain logical bugs. Because of this, it is important to carefully test and review AI generated solutions instead of assuming they are correct.
