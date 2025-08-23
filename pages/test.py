import streamlit as st


import streamlit as st

st.title("🔍 Streamlit st.container Playground")
st.write("Experimenting with all container arguments (border, width, height, alignment, gap, etc.).")

# --- Border & Key demo ---
st.subheader("1. Border and Key")
with st.container(border=True, key="border_demo"):
    st.write("This container has a **border** and a unique key.")
    st.button("Button inside border demo", key="btn1")

with st.container(border=False, key="no_border_demo"):
    st.write("This container has **no border**.")
    st.button("Button inside no border demo", key="btn2")

# --- Width demo ---
st.subheader("2. Width")
with st.container(border=True, width=300, key="fixed_width"):
    st.write("This container has **fixed width = 300px** (shrinked).")

with st.container(border=True, width="stretch", key="stretch_width"):
    st.write("This container **stretches to parent width**.")

# --- Height demo ---
st.subheader("3. Height")
with st.container(border=True, height=150, key="scroll_demo"):
    st.write("This container has **fixed height = 150px**. If content exceeds, it scrolls:")
    for i in range(10):
        st.write(f"Item {i+1}")

with st.container(border=True, height="stretch", key="stretch_height"):
    st.write("This container height **stretches with parent height** (or content).")

# --- Horizontal layout ---
st.subheader("4. Horizontal Layout & Alignment")
with st.container(border=True, horizontal=True, horizontal_alignment="left", gap="small", key="left_aligned"):
    st.write("⬅ Left aligned")
    st.button("A", key="btn_left1")
    st.button("B", key="btn_left2")

with st.container(border=True, horizontal=True, horizontal_alignment="center", gap="medium", key="center_aligned"):
    st.write("⬆ Center aligned")
    st.button("C", key="btn_center1")
    st.button("D", key="btn_center2")

with st.container(border=True, horizontal=True, horizontal_alignment="right", gap="large", key="right_aligned"):
    st.write("➡ Right aligned")
    st.button("E", key="btn_right1")
    st.button("F", key="btn_right2")

with st.container(border=True, horizontal=True, horizontal_alignment="distribute", key="distribute_aligned"):
    st.write("↔ Distributed across full width")
    st.button("G", key="btn_dist1")
    st.button("H", key="btn_dist2")
    st.button("I", key="btn_dist3")

# --- Vertical alignment ---
st.subheader("5. Vertical Alignment (when fixed height is set)")
with st.container(border=True, height=300, vertical_alignment="top", key="vertical_top"):
    st.write("Top aligned element")

with st.container(border=True, height=300, vertical_alignment="center", key="vertical_center"):
    st.write("Center aligned element")

with st.container(border=True, height=300, vertical_alignment="bottom", key="vertical_bottom"):
    st.write("Bottom aligned element")

with st.container(border=True, height=300, vertical_alignment="distribute", key="vertical_distribute"):
    st.write("Item 1")
    st.write("Item 2")
    st.write("Item 3")

# --- Gap demo ---
st.subheader("6. Gap Size")
with st.container(border=True, gap="small", key="gap_small"):
    st.write("Small gap")
    st.button("Button 1")
    st.button("Button 2")

with st.container(border=True, gap="medium", key="gap_medium"):
    st.write("Medium gap")
    st.button("Button 3")
    st.button("Button 4")

with st.container(border=True, gap="large", key="gap_large"):
    st.write("Large gap")
    st.button("Button 5")
    st.button("Button 6")

with st.container(border=True, gap=None, key="gap_none"):
    st.write("No gap at all")
    st.button("Button 7")
    st.button("Button 8")

st.success("Play with resizing the window to really see how width, height, and alignment behave.")


