import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Make the app wider
st.set_page_config(layout="wide")

# Define the low stock alert threshold
LOW_STOCK_THRESHOLD = 1

# App title
st.title("Household Inventory Manager")
st.markdown("Easily manage your household items and their quantities.")

# Define the Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "Inv"

def get_data():
    """
    Reads data from the specified Google Sheet and returns it as a DataFrame.
    """
    try:
        data = conn.read(worksheet=SHEET_NAME, ttl=0)
        data.dropna(subset=['Image', 'Name', 'Quantity'], how='all', inplace=True)
        return data
    except Exception as e:
        st.error(f"Error reading data from Google Sheets: {e}")
        return None

def update_gsheet_quantity_and_date(item_name, new_quantity):
    """
    Updates both the 'Quantity' and 'Date' columns in the Google Sheet for a specific item.
    """
    try:
        current_data = get_data()
        row_index = [i for i, name in enumerate(current_data['Name']) if name == item_name]
        
        if row_index:
            current_data.loc[row_index[0], 'Quantity'] = new_quantity
            now = datetime.now()
            current_date_str = f"{now.month}/{now.day}/{now.year}"
            current_data.loc[row_index[0], 'Date'] = current_date_str
            conn.update(worksheet=SHEET_NAME, data=current_data)
            st.success("Quantity and Date updated successfully!")
        else:
            st.error(f"Item '{item_name}' not found in the inventory.")
    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")
        st.exception(e)

def update_notes_in_gsheet(item_name, new_notes):
    """
    Updates the 'Notes' column in the Google Sheet for a specific item.
    """
    try:
        current_data = get_data()
        row_index = [i for i, name in enumerate(current_data['Name']) if name == item_name]
        
        if row_index:
            current_data.loc[row_index[0], 'Notes'] = new_notes
            conn.update(worksheet=SHEET_NAME, data=current_data)
            st.success("Notes updated successfully!")
        else:
            st.error(f"Item '{item_name}' not found in the inventory.")
    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")
        st.exception(e)

def add_new_item_to_gsheet(image, name, quantity, notes=None):
    """
    Adds a new item by reading the data, appending a new row to the DataFrame,
    and then writing the entire DataFrame back to the Google Sheet.
    """
    try:
        current_data = get_data()
        now = datetime.now()
        date_str = f"{now.month}/{now.day}/{now.year}"
        new_row_df = pd.DataFrame([{
            'Image': image,
            'Name': name,
            'Quantity': quantity,
            'Notes': notes,
            'Date': date_str
        }])
        updated_data = pd.concat([current_data, new_row_df], ignore_index=True)
        conn.update(worksheet=SHEET_NAME, data=updated_data)
        st.success(f"Successfully added '{name}' to the inventory!")
    except Exception as e:
        st.error(f"Error adding new item to Google Sheet: {e}")
        st.exception(e)

def delete_item_from_gsheet(item_name):
    """
    Deletes an item from the Google Sheet based on its name.
    """
    try:
        current_data = get_data()
        if item_name in current_data['Name'].values:
            row_to_delete = current_data[current_data['Name'] == item_name].index
            updated_data = current_data.drop(row_to_delete)
            conn.update(worksheet=SHEET_NAME, data=updated_data)
            st.success(f"Successfully deleted '{item_name}' from the inventory!")
        else:
            st.warning(f"Item '{item_name}' not found.")
    except Exception as e:
        st.error(f"Error deleting item: {e}")
        st.exception(e)

def display_inventory_items(inventory_df, is_low_stock_column=False):
    """
    A helper function to display a list of inventory items.
    """
    if not inventory_df.empty:
        for index, row in inventory_df.iterrows():
            item_name = row.get('Name', 'Unknown Item')
            image_url = row.get('Image', '')
            quantity = row.get('Quantity', 0)
            date = row.get('Date', 'No Date')
            notes = row.get('Notes', '')  # Get the notes from the row

            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 0

            if is_low_stock_column and quantity <= LOW_STOCK_THRESHOLD:
                st.warning(f"Warning: Low stock! Only {quantity} left.")

            col1, col2 = st.columns([1, 4]) 

            with col1:
                if pd.notna(image_url) and image_url.strip() != '':
                    st.image(image_url, width=100)
                else:
                    st.image("https://via.placeholder.com/100?text=No+Image", width=100)

            with col2:
                st.markdown(f"### {item_name}")
                st.write(f"**Quantity:** {quantity}")
                st.write(f"**Last Updated:** {date}")

                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    if st.button("Decrease --", key=f"dec_{index}_{is_low_stock_column}"):
                        new_qty = max(0, quantity - 1)
                        update_gsheet_quantity_and_date(item_name, new_qty)
                        st.rerun() 
                with col_b2:
                    if st.button("Increase ++", key=f"inc_{index}_{is_low_stock_column}"):
                        new_qty = quantity + 1
                        update_gsheet_quantity_and_date(item_name, new_qty)
                        st.rerun()
                with col_b3:
                    if st.button("Delete", key=f"del_{index}_{is_low_stock_column}"):
                        delete_item_from_gsheet(item_name)
                        st.rerun()

                with st.form(key=f"edit_notes_form_{index}_{is_low_stock_column}"):
                    # Added height parameter to make the text area smaller
                    new_notes = st.text_area("Notes", value=notes, height=75, key=f"notes_input_{index}_{is_low_stock_column}")
                    
                    submit_notes = st.form_submit_button("Save Notes")

                    if submit_notes:
                        update_notes_in_gsheet(item_name, new_notes)
                        st.rerun()

            st.markdown("---")
    else:
        st.info("No items in this category.")

def main():
    """Main function to run the Streamlit app."""
    
    inventory_df = get_data()

    if inventory_df is not None and not inventory_df.empty:
        low_stock_df = inventory_df[inventory_df['Quantity'] <= LOW_STOCK_THRESHOLD]
        normal_stock_df = inventory_df[inventory_df['Quantity'] > LOW_STOCK_THRESHOLD]

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Normal Stock")
            display_inventory_items(normal_stock_df, is_low_stock_column=False)
        
        with col_right:
            st.subheader("Low Stock")
            display_inventory_items(low_stock_df, is_low_stock_column=True)

    else:
        st.info("No inventory data found. Please check your Google Sheet or add a new item below.")

    st.markdown("---")
    st.subheader("Add a New Item")

    if 'add_item_key' not in st.session_state:
        st.session_state.add_item_key = 0

    with st.form(key=f"add_item_form_{st.session_state.add_item_key}"):
        new_image_url = st.text_input("Link Gambar", key="image_url_input", help="Paste a link to an image of the item.")
        new_item_name = st.text_input("Nama Barang", key="item_name_input", placeholder="e.g., Chicken, Rice, Shampoo")
        new_quantity = st.number_input("Jumlah", min_value=0, value=1, step=1, key="quantity_input")
        new_notes = st.text_input("Nota", key="notes_input", placeholder="e.g., in the pantry, expiry date")
        
        submit_button = st.form_submit_button("Add Item")

        if submit_button:
            if new_item_name:
                add_new_item_to_gsheet(new_image_url, new_item_name, new_quantity, new_notes)
                st.session_state.add_item_key += 1
                st.rerun()
            else:
                st.error("Please enter a name for the item.")

if __name__ == "__main__":

    main()
