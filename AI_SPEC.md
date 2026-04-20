# AI_SPEC.md

## 1. Goal

This file defines the base rules for AI in this project.

AI must:
- understand structure first
- solve real problems directly
- keep code simple
- keep files and classes maintainable
- avoid unnecessary complexity

---

## 2. Core Rules

### 2.1 Reality First
Use the real project structure, real code, and real constraints.

Do not give generic advice unless it directly helps the task.

### 2.2 Structure First
Before coding, identify:
- module
- package
- responsibility
- data flow
- platform boundary

If structure is unclear, define the structure first.

### 2.3 Minimal Change
Prefer the smallest safe change.

Do not rewrite large areas unless:
- structure is broken
- user asks for refactor
- large change is required

### 2.4 Implementation First
If the user asks for code, give usable code.

Do not stay only at theory level.

### 2.5 No Fake Facts
Do not invent:
- files
- classes
- functions
- dependencies
- architecture decisions

If uncertain, state the assumption clearly.

### 2.6 State Assumptions Clearly
When something cannot be verified, state it directly.

Examples:
- Assuming this package is shared code.
- Assuming this dependency already exists.
- Assuming this screen is Android-only.

---

## 3. Architecture Rules

### 3.1 Clear Responsibility
Each layer, package, file, and class should have one clear job.

Typical split:
- UI: rendering, interaction, UI state
- domain: business logic
- data: repository, storage, network
- platform: OS-specific logic

### 3.2 Simple Data Flow
Prefer clear flow:

input -> state -> render -> side effect -> result

Avoid hidden state changes.

### 3.3 No Premature Abstraction
Do not add abstraction unless it solves a real need:
- reuse
- platform split
- testing
- decoupling

### 3.4 Shared Code Must Stay Shared
Shared code should not contain platform-specific logic without a clear boundary.

Use:
- expect / actual
- interface + implementation
- injected platform service

---

## 4. File and Class Rules

### 4.1 Keep Files Small
Do not put too many classes in one file.

Prefer:
- one main class per file
- one main responsibility per file

### 4.2 Keep Classes Simple
Classes should be easy to understand.

Avoid:
- god classes
- deep inheritance
- wrapper over wrapper
- mixed responsibilities
- complex class trees

If a class is hard to explain, split it.

### 4.3 Split by Responsibility
Do not keep adding logic into the same file just for convenience.

Split by:
- feature
- layer
- responsibility

### 4.4 Clear Naming
Use names that show responsibility clearly.

Prefer:
- `UserRepository`
- `LoadProfileUseCase`
- `TimerUiState`

Avoid:
- `Helper`
- `Manager`
- `Util`
- vague names

### 4.5 New Files Must Be Explicit
When adding a new file, always state:
- file path
- purpose
- why it belongs here

---

## 5. Package Rules

### 5.1 Package Must Have Clear Boundary
Each package should have a clear purpose.

Do not mix unrelated logic into one package.

### 5.2 Add Package Document
When adding a meaningful package, also add a short package document.

Preferred file name:
- `PACKAGE.md`

Purpose:
- explain package responsibility
- reduce scanning the whole package
- help AI understand structure quickly

### 5.3 PACKAGE.md Should Contain
Keep it short:
- purpose
- responsibility
- key files
- dependencies
- what should not be inside

### 5.4 Read Document Before Code
When `PACKAGE.md` exists, read it first.

Default order:
1. read `AI_SPEC.md`
2. read `PACKAGE.md`
3. scan only the directly related code files
4. avoid scanning the whole package unless necessary

### 5.5 Document First
For a new meaningful package, write `PACKAGE.md` first, then add code.

Do not wait until the package becomes large before documenting it.
Update `PACKAGE.md` when the package boundary or responsibility changes.

### 5.6 Scan Only What Is Needed
Do not scan unrelated files or full packages by default.

Read the package document first, then only read files directly related to the task.

---

## 6. Code Rules

### 6.1 Match Existing Style
Follow the current project style:
- naming
- nullability
- state handling
- error handling
- file structure

### 6.2 Keep Code Readable
Prefer:
- small functions
- low nesting
- explicit names
- direct flow

### 6.3 Avoid Overengineering
Do not add:
- unnecessary generics
- unnecessary inheritance
- unnecessary patterns
- unnecessary wrappers
- unnecessary layers

### 6.4 Handle Real Edge Cases
Handle important cases:
- null
- empty
- invalid input
- loading
- lifecycle
- platform differences

Do not add defensive complexity without reason.

### 6.5 Reuse Existing Project Patterns
Before creating new structure, check whether the project already has a similar pattern.

Prefer extending existing valid patterns over introducing a new style.

### 6.6 Comments Only When Useful
Add comments only for:
- non-obvious logic
- important assumptions
- platform-specific constraints

Do not add comments that only repeat the code.

---

## 7. UI Rules

### 7.1 Real Usage First
UI should work well in real use, not only look fine.

### 7.2 Preserve Layout Logic
Do not break:
- spacing
- alignment
- readability
- touch area
- visual hierarchy

### 7.3 Explicit State
UI should clearly show:
- loading
- empty
- success
- error
- disabled
- selected
- editing

### 7.4 No Fake Fixes
Do not fix layout issues with random padding or offsets unless the root cause is clear.

---

## 8. Debug Rules

### 8.1 Find Root Cause First
Start from:
- symptom
- trigger
- layer
- probable cause

Do not suggest random changes.

### 8.2 Distinguish Cause and Effect
Bug source may come from:
- data
- state
- layout
- lifecycle
- timing
- config
- environment

### 8.3 Use Verifiable Fixes
Fixes should be explainable and testable.

---

## 9. Output Rules

Prefer small patch output first.
Use whole file replacement only when patching would be messy, risky, or harder to apply.

### 9.1 Small Patch
Use when only a few lines change.

Provide:
- file
- location
- exact replacement

### 9.2 Whole File
Use when partial patch is messy or risky.

Provide:
- file path
- full file content

### 9.3 Structural Plan
Use when the real issue is architecture.

Provide:
- current issue
- better structure
- affected files
- implementation steps

---

## 10. Priority

When conflict happens, follow this order:

1. correctness
2. compatibility
3. minimal change
4. readability
5. maintainability
6. extensibility

---

## 11. Final Rule

AI must act like a practical project collaborator.

That means:
- understand structure first
- keep files small
- keep classes simple
- split by responsibility
- avoid unnecessary complexity
- provide usable code
- reduce token waste
- use package documents before scanning large code