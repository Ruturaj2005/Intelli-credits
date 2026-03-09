/**
 * NewAppraisal — multi-section form to upload documents and start the appraisal.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { Upload, FileText, CheckCircle2, Building2, IndianRupee, Layers } from 'lucide-react'

const API = '/api'

const SECTORS = [
  'Manufacturing',
  'NBFC',
  'Real Estate',
  'Trading',
  'Infrastructure',
  'Healthcare',
  'Technology',
  'Hospitality',
  'Agriculture',
  'Other',
]

const DOC_ZONES = [
  { field: 'annual_report',    label: 'Annual Report',                icon: '📋', accept: '.pdf',      required: false },
  { field: 'gst_returns',      label: 'GST Returns (GSTR-3B + 2A)',   icon: '🧾', accept: '.pdf,.xlsx', required: false },
  { field: 'bank_statements',  label: 'Bank Statements (12 months)',  icon: '🏦', accept: '.pdf',      required: false },
  { field: 'itr',              label: 'ITR — Last 3 Years',           icon: '📊', accept: '.pdf',      required: false },
  { field: 'legal_documents',  label: 'Legal Documents / Sanctions',  icon: '⚖️', accept: '.pdf',      required: false },
  { field: 'mca_filings',      label: 'MCA / Other Filings',          icon: '🏛️', accept: '.pdf',      required: false },
]

function DropZone({ meta, onFile, file }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles[0]) onFile(meta.field, acceptedFiles[0])
  }, [meta.field, onFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: meta.accept.split(',').reduce((acc, ext) => {
      const mime = ext.trim() === '.pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      return { ...acc, [mime]: [ext.trim()] }
    }, {}),
  })

  return (
    <div
      {...getRootProps()}
      className={`relative rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all duration-300 group overflow-hidden
        ${isDragActive 
          ? 'border-[var(--accent)] scale-105' 
          : file 
          ? 'border-[var(--accent)] bg-[var(--accent)]/5 hover:bg-[var(--accent)]/8' 
          : 'border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface-elevated)]'
        }`}
      style={{ background: file ? 'var(--surface-elevated)' : 'var(--surface)' }}
    >
      <input {...getInputProps()} />
      <div className="flex items-center gap-4 relative z-10">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl transition-all duration-300 ${file ? 'scale-110' : 'group-hover:scale-110'}`}
             style={{ background: file ? 'var(--accent)20' : 'var(--surface-elevated)' }}>
          {file ? <CheckCircle2 size={24} style={{ color: 'var(--accent)' }} /> : <span>{meta.icon}</span>}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text)' }}>
            {meta.label}
          </p>
          {file ? (
            <div className="flex items-center gap-2">
              <p className="text-xs font-mono truncate" style={{ color: 'var(--accent)' }}>
                {file.name}
              </p>
              <span className="text-xs px-2 py-0.5 rounded font-mono" 
                    style={{ background: 'var(--accent)15', color: 'var(--accent)' }}>
                {(file.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ) : (
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              {isDragActive ? 'Drop here...' : 'Drag & drop or click to browse'}
            </p>
          )}
        </div>
        {file && (
          <div className="w-8 h-8 rounded-full flex items-center justify-center animate-scale-in"
               style={{ background: 'var(--accent)', color: 'white' }}>
            ✓
          </div>
        )}
      </div>
      {!file && (
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent opacity-0 group-hover:opacity-5 transition-opacity"
             style={{ transform: 'translateX(-100%)' }}></div>
      )}
    </div>
  )
}

export default function NewAppraisal() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    company_name: '',
    sector: '',
    loan_amount: '',
    qualitative_notes: '',
  })
  const [files, setFiles] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleFile = useCallback((field, file) => {
    setFiles((prev) => ({ ...prev, [field]: file }))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!form.company_name.trim()) {
      setError('Company name is required.')
      return
    }
    if (!form.sector) {
      setError('Please select a sector.')
      return
    }

    setLoading(true)
    const fd = new FormData()
    fd.append('company_name', form.company_name.trim())
    fd.append('sector', form.sector)
    fd.append('loan_amount', form.loan_amount || '0')
    fd.append('qualitative_notes', form.qualitative_notes)

    DOC_ZONES.forEach(({ field }) => {
      if (files[field]) fd.append(field, files[field])
    })

    try {
      const { data } = await axios.post(`${API}/appraisal/start`, fd)
      navigate(`/appraisal/${data.job_id}/pipeline`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start appraisal. Check backend connection.')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-8 py-10">
      {/* Enhanced Header */}
      <div className="mb-10 animate-slide-up">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" 
               style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-dark))' }}>
            <FileText size={24} color="white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-syne font-bold text-3xl" style={{ color: 'var(--text)' }}>
              New Credit Appraisal
            </h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--muted)' }}>
              AI-powered analysis • Sub-30 minute turnaround • Bank-grade compliance
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Company Details */}
        <div className="card p-8 animate-scale-in" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                 style={{ background: 'var(--accent)20', color: 'var(--accent)' }}>
              1
            </div>
            <div>
              <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                Company Information
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                Basic details about the applicant entity
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-5">
            <div className="col-span-2 input-group">
              <label className="input-label flex items-center gap-2">
                <Building2 size={14} style={{ color: 'var(--accent)' }} />
                Company Name *
              </label>
              <input
                className="input-field"
                name="company_name"
                value={form.company_name}
                onChange={handleChange}
                placeholder="e.g. XYZ Manufacturing Pvt. Ltd."
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label flex items-center gap-2">
                <Layers size={14} style={{ color: 'var(--accent)' }} />
                Sector *
              </label>
              <select
                className="input-field"
                name="sector"
                value={form.sector}
                onChange={handleChange}
                required
              >
                <option value="">Select sector...</option>
                {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label className="input-label flex items-center gap-2">
                <IndianRupee size={14} style={{ color: 'var(--accent)' }} />
                Loan Amount Requested (₹ Crore)
              </label>
              <input
                className="input-field font-mono"
                name="loan_amount"
                type="number"
                min="0"
                step="0.01"
                value={form.loan_amount}
                onChange={handleChange}
                placeholder="e.g. 15.00"
              />
            </div>          <div className="col-span-2 input-group">
              <label className="input-label">Qualitative Notes (Optional)</label>
              <textarea
                className="input-field"
                name="qualitative_notes"
                value={form.qualitative_notes}
                onChange={handleChange}
                placeholder="Add any special instructions, context, or observations..."
                rows="3"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Document Upload */}
        <div className="card p-8 animate-scale-in" style={{ animationDelay: '200ms' }}>
          <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                 style={{ background: 'var(--accent2)20', color: 'var(--accent2)' }}>
              2
            </div>
            <div>
              <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                Financial Documents
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                Upload financial statements • Max {50}MB per file • PDF preferred
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {DOC_ZONES.map((meta, idx) => (
              <div key={meta.field} className="animate-slide-up" style={{ animationDelay: `${300 + idx * 50}ms` }}>
                <DropZone
                  meta={meta}
                  onFile={handleFile}
                  file={files[meta.field]}
                />
              </div>
            ))}
          </div>
          <div className="mt-5 p-4 rounded-lg flex items-center justify-between" 
               style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-3">
              <Upload size={18} style={{ color: 'var(--accent)' }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                  {Object.values(files).filter(Boolean).length} / {DOC_ZONES.length} files uploaded
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  {Object.values(files).filter(Boolean).length === 0 
                    ? 'Upload documents for better analysis accuracy'
                    : 'Engine will process all uploaded documents'
                  }
                </p>
              </div>
            </div>
            {Object.values(files).filter(Boolean).length > 0 && (
              <div className="px-3 py-1.5 rounded-full font-mono text-xs font-semibold"
                   style={{ background: 'var(--accent)15', color: 'var(--accent)' }}>
                Ready
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="card p-5 border-2 animate-scale-in" 
               style={{ borderColor: 'var(--danger)', background: 'var(--danger)10' }}>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                   style={{ background: 'var(--danger)20' }}>
                <span style={{ color: 'var(--danger)' }}>!</span>
              </div>
              <div>
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--danger)' }}>
                  Submission Error
                </p>
                <p className="text-xs" style={{ color: 'var(--danger-dark)' }}>
                  {error}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex items-center justify-between pt-6 animate-slide-up" style={{ animationDelay: '400ms' }}>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn-secondary"
          >
            ← Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex items-center gap-3 px-10"
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span>Start Appraisal</span>
                <span className="text-lg">→</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
