import { useState } from "react";
import { useDocuments } from "../hooks/useDocuments";
import { Upload, Trash2, FileText, RefreshCw } from "lucide-react";

export default function Documents() {
  const { documents, loading, loadDocuments, uploadDocument, deleteDocument } = useDocuments();
  const [file, setFile] = useState(null);
  const [strategy, setStrategy] = useState("recursive");
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file, strategy);
      setFile(null);
      document.getElementById('file-upload').value = "";
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-8 h-full overflow-y-auto bg-gray-50">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold text-gray-800">Knowledge Base</h2>
        <button onClick={loadDocuments} className="text-gray-500 hover:text-blue-600 flex items-center space-x-1 bg-white border px-3 py-1.5 rounded shadow-sm">
          <RefreshCw size={16} /><span>Refresh</span>
        </button>
      </div>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border mb-8">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">Upload New Document</h3>
        <form onSubmit={handleUpload} className="flex flex-col md:flex-row items-end gap-4">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium mb-1 text-gray-700">PDF File</label>
            <input 
              id="file-upload"
              type="file" 
              accept=".pdf" 
              onChange={(e) => setFile(e.target.files[0])}
              className="block w-full border border-gray-300 p-2 rounded-lg text-sm bg-gray-50 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <div className="w-full md:w-64">
            <label className="block text-sm font-medium mb-1 text-gray-700">Chunking Strategy</label>
            <select 
              value={strategy} 
              onChange={(e) => setStrategy(e.target.value)}
              className="block w-full border border-gray-300 p-2.5 rounded-lg bg-gray-50 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="recursive">Recursive Character</option>
              <option value="fixed">Fixed Size</option>
              <option value="semantic">Semantic</option>
            </select>
          </div>
          <button 
            type="submit" 
            disabled={!file || uploading}
            className="bg-blue-600 text-white px-5 py-2.5 rounded-lg flex items-center justify-center space-x-2 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors w-full md:w-auto"
          >
            {uploading ? <RefreshCw size={18} className="animate-spin" /> : <Upload size={18} />}
            <span>{uploading ? "Uploading..." : "Upload"}</span>
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Document Name</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Strategy</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Chunks</th>
              <th className="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {loading && documents.length === 0 && (
              <tr><td colSpan="5" className="px-6 py-8 text-center text-gray-500">Loading documents...</td></tr>
            )}
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap flex items-center space-x-3">
                  <div className="p-2 bg-blue-50 rounded text-blue-600">
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{doc.filename}</div>
                    <div className="text-xs text-gray-500">{(doc.file_size_bytes / 1024).toFixed(1)} KB • v{doc.version}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    doc.status === 'ready' ? 'bg-green-100 text-green-700 border border-green-200' : 
                    doc.status === 'processing' ? 'bg-yellow-100 text-yellow-700 border border-yellow-200' : 
                    'bg-red-100 text-red-700 border border-red-200'
                  }`}>
                    {doc.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 capitalize">{doc.chunking_strategy}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{doc.chunk_count || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={async () => {
                    if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
                    try {
                      await deleteDocument(doc.id);
                    } catch (err) {
                      alert("Delete failed: " + err.message);
                    }
                  }} className="text-gray-400 hover:text-red-600 transition-colors p-2 hover:bg-red-50 rounded-lg">
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
            {!loading && documents.length === 0 && (
              <tr><td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                <div className="flex flex-col items-center">
                  <FileText size={48} className="text-gray-300 mb-4" />
                  <p>No documents found. Upload a PDF to get started.</p>
                </div>
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
