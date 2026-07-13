# TODO

## 1) Plan (before editing)
- [x] Inspect current `app.py` UI and where CSS/HTML breaks Streamlit widgets.
- [x] Identify the minimal safe Streamlit-native layout and components to replace brittle HTML wrappers.
- [ ] Decide a new visual system: consistent spacing, typography scale, button styles, and background.


## 2) Implement Streamlit-native UI rewrite
- [ ] Remove large HTML topbar/step wrappers and all CSS that targets them.
- [x] Rebuild header and sections using Streamlit components (`st.columns`, `st.container`, `st.subheader`, `st.caption`).


- [ ] Keep only safe CSS overrides (inputs/buttons/data_editor borders) without heavy `.stApp` background hacks.
- [ ] Fix typography by relying on Streamlit defaults + small, consistent `font-size` overrides.
- [ ] Layout compactness: reduce heights, use 2 columns where appropriate, remove vertical “wizard” spacing.


## 3) Improve animations/scroll
- [x] Remove any animation-related CSS or transitions.
- [x] Limit expanders/text areas heights.


## 4) Verify
- [ ] Run `python -m py_compile app.py`.
- [ ] Run `streamlit run app.py` and visually verify.

