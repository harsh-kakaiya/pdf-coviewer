from pdf2image import convert_from_bytes
import streamlit as st
import websockets
import asyncio
import json
import requests
from io import BytesIO
import PyPDF2

# Constants
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

class PDFViewer:
    def __init__(self):
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        if 'viewer_count' not in st.session_state:
            st.session_state.viewer_count = 0
        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False
        if 'room_id' not in st.session_state:
            st.session_state.room_id = None
        if 'pdf_file' not in st.session_state:
            st.session_state.pdf_file = None
        if 'pdf_reader' not in st.session_state:
            st.session_state.pdf_reader = None

    def upload_pdf(self, file, room_id):
        files = {'file': file}
        response = requests.post(f"{BACKEND_URL}/upload/{room_id}", files=files)
        return response.status_code == 200

    async def connect_websocket(self):
        uri = f"{WS_URL}/ws/{st.session_state.room_id}"
        try:
            async with websockets.connect(uri) as websocket:
                if st.session_state.is_admin:
                    await websocket.send(json.dumps({"type": "admin_connect"}))
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        if data["type"] == "page_update":
                            st.session_state.current_page = data["page"]
                        elif data["type"] == "viewer_count":
                            st.session_state.viewer_count = data["count"]
                            
                    except websockets.ConnectionClosed:
                        st.error("Connection lost. Please refresh the page.")
                        break
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

    async def render_ui(self):
        st.title("PDF Co-Viewer")
        
        # Room setup
        col1, col2 = st.columns([2, 1])
        with col1:
            room_id = st.text_input("Enter Room ID", key="room_input")
        with col2:
            is_admin = st.checkbox("Join as Admin", key="admin_checkbox")

        if room_id:
            st.session_state.room_id = room_id
            st.session_state.is_admin = is_admin

            # File upload
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
            if uploaded_file is not None:
                if st.session_state.pdf_file != uploaded_file:
                    st.session_state.pdf_file = uploaded_file
                    st.session_state.pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    if self.upload_pdf(uploaded_file, room_id):
                        st.success("PDF uploaded successfully!")
                    else:
                        st.error("Error uploading PDF")

                # PDF viewer
                try:
                    num_pages = len(st.session_state.pdf_reader.pages)

                    # Navigation controls
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col1:
                        if st.session_state.is_admin and st.button("Previous"):
                            if st.session_state.current_page > 1:
                                st.session_state.current_page -= 1
                                await self.send_page_change(st.session_state.current_page)
                    with col2:
                        if st.session_state.is_admin and st.button("Next"):
                            if st.session_state.current_page < num_pages:
                                st.session_state.current_page += 1
                                await self.send_page_change(st.session_state.current_page)
                    with col3:
                        st.write(f"Page: {st.session_state.current_page}/{num_pages}")
                    with col4:
                        st.write(f"Viewers: {st.session_state.viewer_count}")

                    # Convert current PDF page to image using pdf2image
                    page = st.session_state.pdf_reader.pages[st.session_state.current_page - 1]
                    pdf_bytes = BytesIO(uploaded_file.read())  # Convert the uploaded file into a byte stream
                    images = convert_from_bytes(pdf_bytes.read(), first_page=st.session_state.current_page, last_page=st.session_state.current_page)

                    # Display the image
                    if images:
                        st.image(images[0], use_column_width=True)
                    else:
                        st.write("No image found for this PDF page.")

                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")

    async def send_page_change(self, page_number):
        async with websockets.connect(f"{WS_URL}/ws/{st.session_state.room_id}") as websocket:
            await websocket.send(json.dumps({"type": "page_change", "page": page_number}))

# Main function to run the app
def main():
    viewer = PDFViewer()
    asyncio.run(viewer.render_ui())  # Correctly calling the async method

if __name__ == "__main__":
    main()
