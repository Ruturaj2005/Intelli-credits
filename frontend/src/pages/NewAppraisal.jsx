/**
 * NewAppraisal — multi-section form to upload documents and start the appraisal.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

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
      className={`relative rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all
        ${isDragActive ? 'border-[#00d4aa] bg-[#00d4aa]/5' : file ? 'border-[#00d4aa]/40 bg-[#00d4aa]/5' : 'border-[#1a2530] hover:border-[#4a6070] bg-[#0a0f12]'}`}
    >
      <input {...getInputProps()} />
      <div className="flex items-center gap-3">
        <span className="text-2xl">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[#e8f0f5]">{meta.label}</p>
          {file ? (
            <p className="text-[11px] text-[#00d4aa] font-mono truncate mt-0.5">{file.name}</p>
          ) : (
            <p className="text-[11px] text-[#4a6070] mt-0.5">
              {isDragActive ? 'Drop here...' : 'Drag & drop or click to upload'}
            </p>
          )}
        </div>
        {file && <span className="text-[#00d4aa] text-lg">✓</span>}
      </div>
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
    <div className="max-w-4xl mx-auto px-8 py-8 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-syne font-bold text-2xl text-[#e8f0f5]">New Credit Appraisal</h1>
        <p className="text-[#4a6070] text-sm mt-1">
          Upload financial documents and let the AI engine generate a full CAM in minutes.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Section 1: Company Details */}
        <div className="card p-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-5 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00d4aa]/20 text-[#00d4aa] text-xs flex items-center justify-center font-mono font-bold">1</span>
            Company Details
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs text-[#4a6070] mb-1.5 uppercase tracking-wider">Company Name *</label>
              <input
                className="input-field"
                name="company_name"
                value={form.company_name}
                onChange={handleChange}
                placeholder="e.g. XYZ Manufacturing Pvt. Ltd."
                required
              />
            </div>
            <div>
              <label className="block text-xs text-[#4a6070] mb-1.5 uppercase tracking-wider">Sector *</label>
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
            <div>
              <label className="block text-xs text-[#4a6070] mb-1.5 uppercase tracking-wider">
                Loan Amount Requested (Rs. Crore)
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
            </div>
          </div>
        </div>

        {/* Section 2: Document Upload */}
        <div className="card p-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-2 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00d4aa]/20 text-[#00d4aa] text-xs flex items-center justify-center font-mono font-bold">2</span>
            Financial Documents
          </h2>
          <p className="text-[11px] text-[#4a6070] mb-5 ml-8">
            Upload up to 6 document types. PDF preferred. Max {50}MB per file.
          </p>
          <div className="grid grid-cols-2 gap-3">
            {DOC_ZONES.map((meta) => (
              <DropZone
                key={meta.field}
                meta={meta}
                onFile={handleFile}
                file={files[meta.field]}
              />
            ))}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span className="text-[11px] text-[#4a6070]">
              {Object.values(files).filter(Boolean).length} / {DOC_ZONES.length} files uploaded
            </span>
            {Object.values(files).filter(Boolean).length === 0 && (
              <span className="text-[11px] text-[#ffd166]">
                (Engine will work with available data — upload more for better accuracy)
              </span>
            )}
          </div>
        </div>

        {/* Section 3: Qualitative Notes */}
        <div className="card p-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-5 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[#00d4aa]/20 text-[#00d4aa] text-xs flex items-center justify-center font-mono font-bold">3</span>
            Credit Officer Field Observations
          </h2>
          <textarea
            className="input-field"
            name="qualitative_notes"
            value={form.qualitative_notes}
            onChange={handleChange}
            rows={5}
            placeholder={`E.g. Factory found operating at 40% capacity. Management was evasive about the December dip in sales. Unit was visited on 15 Feb, equipment appears well-maintained but order book is thin for Q1.`}
          />
          <p className="text-[11px] text-[#4a6070] mt-2">
            These notes will be factored into the AI scoring. A before/after comparison will be shown in results.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-[#ef476f]/30 bg-[#ef476f]/10 px-5 py-4">
            <p className="text-sm text-[#ef476f]">⚠ {error}</p>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-[#4a6070]">
              Estimated completion: <span className="text-[#00d4aa] font-mono">3–6 minutes</span>
            </p>
            <p className="text-[11px] text-[#2a3a4a] mt-0.5">vs industry average of 10–15 business days</p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary px-10 py-4 text-base"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-[#020608]/30 border-t-[#020608] rounded-full animate-spin" />
                Starting Engine...
              </span>
            ) : (
              '⚡ Run Appraisal Engine'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
