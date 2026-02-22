import { useState } from "react";

export default function StudentUpload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];

    if (!selectedFile) return;

    if (!selectedFile.type.startsWith("image/")) {
      setMessage("Only image files are allowed.");
      return;
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setMessage("");
  };

  const handleSubmit = async () => {
    if (!file) {
      setMessage("Please select an image.");
      return;
    }

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch("http://localhost:8080/upload", {
        method: "POST",
        body: formData,
      });

      await response.json();
      setMessage("Upload successful!");
    } catch (error) {
      setMessage("Backend not connected yet.");
    }
  };

  return (
    <div className="p-8 text-white">
      <h1 className="text-2xl font-bold mb-6">Upload Image</h1>

      <div className="bg-gray-800 p-6 rounded-lg w-full max-w-md">

        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="block w-full mb-4 text-sm text-gray-300
                     file:mr-4 file:py-2 file:px-4
                     file:rounded file:border-0
                     file:text-sm file:font-semibold
                     file:bg-blue-600 file:text-white
                     hover:file:bg-blue-700"
        />

        {preview && (
          <img
            src={preview}
            alt="Preview"
            className="mb-4 rounded-lg max-h-64 object-contain"
          />
        )}

        <button
          onClick={handleSubmit}
          className="w-full bg-blue-600 hover:bg-blue-700 py-2 rounded"
        >
          Submit
        </button>

        {message && (
          <p className="mt-4 text-sm text-yellow-400">
            {message}
          </p>
        )}
      </div>
    </div>
  );
}