/**
 * NewAppraisal — multi-section form to upload documents and start the appraisal.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { Upload, FileText, CheckCircle2, Building2, IndianRupee, Layers, Eye, Users, AlertCircle, Info } from 'lucide-react'

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
  { field: 'rating_report',    label: 'Rating Agency Report',         icon: '⭐', accept: '.pdf',      required: false, helpText: 'CRISIL, ICRA, CARE, India Ratings, or Brickwork - Optional but recommended for loans above ₹5 Cr' },
  { field: 'cibil_report',     label: 'CIBIL Commercial Report',      icon: '💳', accept: '.pdf',      required: false, helpText: 'CCR or CMR report from CIBIL portal' },
  { field: 'shareholding',     label: 'Shareholding Pattern',         icon: '📊', accept: '.pdf',      required: false, helpText: 'Latest shareholding from MCA or annual report' },
  { field: 'sanction_letters', label: 'Existing Bank Sanction Letters', icon: '📝', accept: '.pdf',   required: false, helpText: 'Current loan limits from existing lenders' },
  { field: 'audited_financials', label: 'Audited Financial Statements', icon: '📈', accept: '.pdf',  required: false, helpText: 'CA certified statements if separate from annual report' },
]

// Industry-specific premises options
const PREMISES_OPTIONS = {
  'Manufacturing': ['Factory and Plant', 'Warehouse and Storage', 'Processing Unit', 'Assembly Unit'],
  'NBFC': ['Registered Office', 'Branch Office', 'Loan Processing Centre'],
  'Real Estate': ['Project Site Under Construction', 'Completed Project Site', 'Land Bank', 'Corporate Office'],
  'Trading': ['Retail Outlet', 'Wholesale Godown', 'Distribution Centre', 'Corporate Office'],
  'Infrastructure': ['Project Construction Site', 'Operational Asset', 'Corporate Office'],
  'Healthcare': ['Hospital and Clinical Facility', 'Diagnostic Centre', 'Pharmaceutical Unit', 'Corporate Office'],
  'Technology': ['Development Office', 'Data Centre', 'Corporate Office'],
  'Hospitality': ['Hotel and Resort Property', 'Restaurant and F&B Outlet', 'Corporate Office'],
  'Agriculture': ['Farm and Agricultural Land', 'Processing and Storage Unit', 'Cold Storage Facility', 'Corporate Office'],
  'Other': ['Business Premises', 'Corporate Office', 'Operational Site']
}

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
  const [activeTab, setActiveTab] = useState('factory')
  
  const [qualitative, setQualitative] = useState({
    factory_visit: {
      visit_conducted: 'yes',
      visit_date: '',
      visited_by: '',
      premises_type: '',
      capacity_utilization: '',
      asset_condition: '',
      workforce_observations: '',
      inventory_levels: '',
      environmental_compliance: '',
      collateral_verification: '',
      overall_impression: '',
      specific_observations: ''
    },
    management_interview: {
      interview_conducted: 'yes',
      interview_date: '',
      persons_interviewed: '',
      promoter_experience: '',
      second_line_management: '',
      transparency: '',
      business_vision: '',
      order_book_visibility: '',
      promoter_contribution: '',
      related_party_concerns: '',
      key_positives: '',
      key_concerns: ''
    }
  })

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleFile = useCallback((field, file) => {
    setFiles((prev) => ({ ...prev, [field]: file }))
  }, [])

  const handleQualitativeChange = (section, field, value) => {
    setQualitative(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }))
  }

  // Sector-specific field visibility
  const showField = (field) => {
    const sector = form.sector
    if (!sector) return true
    
    if (field === 'capacity_utilization') {
      return ['Manufacturing', 'Infrastructure', 'Healthcare', 'Agriculture', 'Hospitality'].includes(sector)
    }
    if (field === 'inventory_levels') {
      return ['Manufacturing', 'Trading', 'Healthcare', 'Agriculture'].includes(sector)
    }
    if (field === 'environmental_compliance') {
      return ['Manufacturing', 'Infrastructure', 'Agriculture', 'Real Estate'].includes(sector)
    }
    if (field === 'order_book_visibility') {
      return !['NBFC', 'Real Estate'].includes(sector)
    }
    return true
  }

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
    fd.append('qualitative_inputs', JSON.stringify(qualitative))

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

        {/* Section 3: Primary Due Diligence */}
        <div className="card p-8 animate-scale-in" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                 style={{ background: 'var(--success)20', color: 'var(--success)' }}>
              3
            </div>
            <div className="flex-1">
              <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                Primary Due Diligence
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                Site Visit and Management Interview — RBI Mandatory Assessment
              </p>
            </div>
          </div>

          {/* Banner */}
          <div className="mb-6 p-4 rounded-lg flex items-start gap-3" 
               style={{ background: 'var(--accent)10', border: '1px solid var(--accent)30' }}>
            <AlertCircle size={18} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
            <p className="text-sm" style={{ color: 'var(--text)' }}>
              <strong>These qualitative inputs contribute 30% to the final credit score.</strong> Inputs should be filled by the visiting credit officer after conducting site visit and management interview as per RBI guidelines on credit appraisal.
            </p>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--border)' }}>
            <button
              type="button"
              onClick={() => setActiveTab('factory')}
              className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm transition-all ${
                activeTab === 'factory' ? 'border-b-2' : ''
              }`}
              style={{
                color: activeTab === 'factory' ? 'var(--accent)' : 'var(--muted)',
                borderColor: activeTab === 'factory' ? 'var(--accent)' : 'transparent'
              }}
            >
              <Eye size={16} />
              Factory / Site Visit
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('management')}
              className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm transition-all ${
                activeTab === 'management' ? 'border-b-2' : ''
              }`}
              style={{
                color: activeTab === 'management' ? 'var(--accent)' : 'var(--muted)',
                borderColor: activeTab === 'management' ? 'var(--accent)' : 'transparent'
              }}
            >
              <Users size={16} />
              Management Interview
            </button>
          </div>

          {/* Factory Visit Tab */}
          {activeTab === 'factory' && (
            <div className="space-y-5 animate-slide-up">
              <div className="input-group">
                <label className="input-label">Was a site visit conducted?</label>
                <div className="flex gap-4">
                  {['yes', 'no', 'not_applicable'].map(opt => (
                    <label key={opt} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="visit_conducted"
                        value={opt}
                        checked={qualitative.factory_visit.visit_conducted === opt}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'visit_conducted', e.target.value)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm capitalize" style={{ color: 'var(--text)' }}>
                        {opt.replace('_', ' ')}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {qualitative.factory_visit.visit_conducted === 'yes' ? (
                <>
                  <div className="grid grid-cols-2 gap-5">
                    <div className="input-group">
                      <label className="input-label">Visit Date</label>
                      <input
                        type="date"
                        className="input-field"
                        value={qualitative.factory_visit.visit_date}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'visit_date', e.target.value)}
                      />
                    </div>
                    <div className="input-group">
                      <label className="input-label">Visited By (Name & Designation)</label>
                      <input
                        type="text"
                        className="input-field"
                        placeholder="e.g. John Doe - Senior Credit Officer"
                        value={qualitative.factory_visit.visited_by}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'visited_by', e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Type of Premises Visited</label>
                    <select
                      className="input-field"
                      value={qualitative.factory_visit.premises_type}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'premises_type', e.target.value)}
                    >
                      <option value="">Select premises type...</option>
                      {form.sector && PREMISES_OPTIONS[form.sector]?.map(opt => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </div>

                  {showField('capacity_utilization') && (
                    <div className="input-group">
                      <label className="input-label">Capacity Utilization</label>
                      <select
                        className="input-field"
                        value={qualitative.factory_visit.capacity_utilization}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'capacity_utilization', e.target.value)}
                      >
                        <option value="">Select...</option>
                        <option value="above_80">Above 80% - Excellent</option>
                        <option value="60_to_80">60-80% - Good</option>
                        <option value="40_to_60">40-60% - Moderate</option>
                        <option value="below_40">Below 40% - Poor</option>
                      </select>
                    </div>
                  )}

                  <div className="input-group">
                    <label className="input-label">
                      {form.sector === 'Manufacturing' ? 'Machinery & Asset Condition' 
                       : form.sector === 'Healthcare' ? 'Equipment & Facility Condition'
                       : form.sector === 'Technology' ? 'IT Infrastructure Condition'
                       : 'Asset Condition'}
                    </label>
                    <select
                      className="input-field"
                      value={qualitative.factory_visit.asset_condition}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'asset_condition', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="modern_well_maintained">Modern & Well Maintained</option>
                      <option value="adequate">Adequate - Regular Maintenance Visible</option>
                      <option value="average">Average - Some Aging Visible</option>
                      <option value="poor">Poor - Maintenance Concerns</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">
                      {form.sector === 'Technology' ? 'Employee Strength & Attrition'
                       : form.sector === 'Healthcare' ? 'Staff Strength & Quality'
                       : 'Workforce Observations'}
                    </label>
                    <select
                      className="input-field"
                      value={qualitative.factory_visit.workforce_observations}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'workforce_observations', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="adequate_skilled">Adequate & Skilled</option>
                      <option value="adequate_training_needed">Adequate but Training Needed</option>
                      <option value="understaffed">Understaffed</option>
                      <option value="high_attrition">High Attrition Concern</option>
                    </select>
                  </div>

                  {showField('inventory_levels') && (
                    <div className="input-group">
                      <label className="input-label">Inventory Levels & Management</label>
                      <select
                        className="input-field"
                        value={qualitative.factory_visit.inventory_levels}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'inventory_levels', e.target.value)}
                      >
                        <option value="">Select...</option>
                        <option value="optimal">Optimal - Well Organized</option>
                        <option value="adequate">Adequate</option>
                        <option value="excess">Excess Inventory - Blockage Concern</option>
                        <option value="depleted">Depleted - Supply Chain Issues</option>
                      </select>
                    </div>
                  )}

                  {showField('environmental_compliance') && (
                    <div className="input-group">
                      <label className="input-label flex items-center gap-2">
                        Environmental & Statutory Compliance
                        <Info size={14} style={{ color: 'var(--muted)' }} />
                      </label>
                      <select
                        className="input-field"
                        value={qualitative.factory_visit.environmental_compliance}
                        onChange={(e) => handleQualitativeChange('factory_visit', 'environmental_compliance', e.target.value)}
                      >
                        <option value="">Select...</option>
                        <option value="full_compliance">Full Compliance - All Clearances</option>
                        <option value="mostly_compliant">Mostly Compliant - Minor Gaps</option>
                        <option value="partial_compliance">Partial Compliance - Action Required</option>
                        <option value="non_compliant">Non-Compliant - Major Concerns</option>
                      </select>
                      {form.sector === 'Manufacturing' && (
                        <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
                          Check: Pollution Control Board consent, Factory license, Fire NOC
                        </p>
                      )}
                      {form.sector === 'Healthcare' && (
                        <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
                          Check: NABH/NABL accreditation, Biomedical waste management, Drug license
                        </p>
                      )}
                    </div>
                  )}

                  <div className="input-group">
                    <label className="input-label">Collateral Verification (if applicable)</label>
                    <select
                      className="input-field"
                      value={qualitative.factory_visit.collateral_verification}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'collateral_verification', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="verified_adequate">Verified & Adequate Value</option>
                      <option value="verified_marginal">Verified but Marginal Value</option>
                      <option value="not_verified">Not Verified Yet</option>
                      <option value="not_applicable">Not Applicable</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Overall Impression of Site</label>
                    <select
                      className="input-field"
                      value={qualitative.factory_visit.overall_impression}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'overall_impression', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="very_positive">Very Positive</option>
                      <option value="positive">Positive</option>
                      <option value="neutral">Neutral</option>
                      <option value="negative">Negative</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">
                      Specific Observations (Free Text)
                      <span className="text-xs ml-2" style={{ color: 'var(--muted)' }}>
                        {qualitative.factory_visit.specific_observations.length}/1000 characters
                      </span>
                    </label>
                    <textarea
                      className="input-field"
                      rows="4"
                      maxLength="1000"
                      placeholder="Detailed observations from the site visit..."
                      value={qualitative.factory_visit.specific_observations}
                      onChange={(e) => handleQualitativeChange('factory_visit', 'specific_observations', e.target.value)}
                    />
                  </div>
                </>
              ) : (
                <div className="p-6 rounded-lg text-center" style={{ background: 'var(--surface-elevated)' }}>
                  <p className="text-sm" style={{ color: 'var(--muted)' }}>
                    {qualitative.factory_visit.visit_conducted === 'not_applicable' 
                      ? 'Site visit not applicable for this appraisal. Factory visit scoring will be neutral.'
                      : 'Site visit not conducted. Factory visit scoring will be neutral.'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Management Interview Tab */}
          {activeTab === 'management' && (
            <div className="space-y-5 animate-slide-up">
              <div className="input-group">
                <label className="input-label">Was a management interview conducted?</label>
                <div className="flex gap-4">
                  {['yes', 'no'].map(opt => (
                    <label key={opt} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="interview_conducted"
                        value={opt}
                        checked={qualitative.management_interview.interview_conducted === opt}
                        onChange={(e) => handleQualitativeChange('management_interview', 'interview_conducted', e.target.value)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm capitalize" style={{ color: 'var(--text)' }}>
                        {opt}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {qualitative.management_interview.interview_conducted === 'yes' ? (
                <>
                  <div className="grid grid-cols-2 gap-5">
                    <div className="input-group">
                      <label className="input-label">Interview Date</label>
                      <input
                        type="date"
                        className="input-field"
                        value={qualitative.management_interview.interview_date}
                        onChange={(e) => handleQualitativeChange('management_interview', 'interview_date', e.target.value)}
                      />
                    </div>
                    <div className="input-group">
                      <label className="input-label">Persons Interviewed (Names & Designations)</label>
                      <input
                        type="text"
                        className="input-field"
                        placeholder="e.g. Rajesh Kumar (MD), Priya Singh (CFO)"
                        value={qualitative.management_interview.persons_interviewed}
                        onChange={(e) => handleQualitativeChange('management_interview', 'persons_interviewed', e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Promoter / Management Experience in Industry</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.promoter_experience}
                      onChange={(e) => handleQualitativeChange('management_interview', 'promoter_experience', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="more_than_15">More than 15 years</option>
                      <option value="10_to_15">10-15 years</option>
                      <option value="5_to_10">5-10 years</option>
                      <option value="less_than_5">Less than 5 years</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Second Line Management Strength</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.second_line_management}
                      onChange={(e) => handleQualitativeChange('management_interview', 'second_line_management', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="strong">Strong - Qualified Team in Place</option>
                      <option value="adequate">Adequate</option>
                      <option value="weak">Weak - Key Man Risk</option>
                      <option value="single_person">Single Person Dependency</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Transparency & Information Quality</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.transparency}
                      onChange={(e) => handleQualitativeChange('management_interview', 'transparency', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="very_transparent">Very Transparent - Proactive Disclosure</option>
                      <option value="transparent">Transparent</option>
                      <option value="guarded">Guarded - Limited Information</option>
                      <option value="not_cooperative">Not Cooperative</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Business Vision & Strategy</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.business_vision}
                      onChange={(e) => handleQualitativeChange('management_interview', 'business_vision', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="clear">Clear & Achievable Plans</option>
                      <option value="moderate">Moderate Clarity</option>
                      <option value="vague">Vague</option>
                      <option value="no_direction">No Clear Direction</option>
                    </select>
                  </div>

                  {showField('order_book_visibility') && (
                    <div className="input-group">
                      <label className="input-label">
                        {['Technology', 'NBFC'].includes(form.sector) 
                          ? 'Customer Pipeline & Conversion Visibility'
                          : 'Order Book / Revenue Visibility'}
                      </label>
                      <select
                        className="input-field"
                        value={qualitative.management_interview.order_book_visibility}
                        onChange={(e) => handleQualitativeChange('management_interview', 'order_book_visibility', e.target.value)}
                      >
                        <option value="">Select...</option>
                        <option value="more_than_6_months">More than 6 months visibility</option>
                        <option value="3_to_6_months">3-6 months visibility</option>
                        <option value="1_to_3_months">1-3 months visibility</option>
                        <option value="uncertain">Uncertain / Spot Business</option>
                      </select>
                    </div>
                  )}

                  <div className="input-group">
                    <label className="input-label">Promoter Skin in the Game (Contribution %)</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.promoter_contribution}
                      onChange={(e) => handleQualitativeChange('management_interview', 'promoter_contribution', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="more_than_33">More than 33% - Strong Commitment</option>
                      <option value="25_to_33">25-33% - Adequate</option>
                      <option value="15_to_25">15-25% - Minimum RBI Requirement</option>
                      <option value="below_15">Below 15% - Concern</option>
                      <option value="none">No Contribution</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Related Party Transactions & Concerns</label>
                    <select
                      className="input-field"
                      value={qualitative.management_interview.related_party_concerns}
                      onChange={(e) => handleQualitativeChange('management_interview', 'related_party_concerns', e.target.value)}
                    >
                      <option value="">Select...</option>
                      <option value="none">None - Clean Structure</option>
                      <option value="minor">Minor - Well Disclosed</option>
                      <option value="moderate">Moderate - Needs Monitoring</option>
                      <option value="significant">Significant Concerns</option>
                      <option value="undisclosed">Undisclosed / Hidden</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">
                      Key Positives from Interview
                      <span className="text-xs ml-2" style={{ color: 'var(--muted)' }}>
                        {qualitative.management_interview.key_positives.length}/500 characters
                      </span>
                    </label>
                    <textarea
                      className="input-field"
                      rows="3"
                      maxLength="500"
                      placeholder="Key strengths observed during the interview..."
                      value={qualitative.management_interview.key_positives}
                      onChange={(e) => handleQualitativeChange('management_interview', 'key_positives', e.target.value)}
                    />
                  </div>

                  <div className="input-group">
                    <label className="input-label">
                      Key Concerns from Interview
                      <span className="text-xs ml-2" style={{ color: 'var(--muted)' }}>
                        {qualitative.management_interview.key_concerns.length}/500 characters
                      </span>
                    </label>
                    <textarea
                      className="input-field"
                      rows="3"
                      maxLength="500"
                      placeholder="Risk factors or concerns noted during the interview..."
                      value={qualitative.management_interview.key_concerns}
                      onChange={(e) => handleQualitativeChange('management_interview', 'key_concerns', e.target.value)}
                    />
                  </div>
                </>
              ) : (
                <div className="p-6 rounded-lg text-center" style={{ background: 'var(--surface-elevated)' }}>
                  <p className="text-sm" style={{ color: 'var(--muted)' }}>
                    Management interview not conducted. Management interview scoring will be neutral.
                  </p>
                </div>
              )}
            </div>
          )}
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
