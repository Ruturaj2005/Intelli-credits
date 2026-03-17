/**
 * NewAppraisal — multi-step wizard with entity onboarding, loan application, and appraisal.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { Upload, FileText, CheckCircle2, Building2, IndianRupee, Layers, Eye, Users, AlertCircle, Info, ArrowLeft, ArrowRight, Check } from 'lucide-react'

const API = '/api'

// Helper function to safely extract error messages from API responses
const getErrorMessage = (err, fallback = 'An error occurred') => {
  if (typeof err === 'string') return err
  
  const detail = err.response?.data?.detail
  if (!detail) return fallback
  
  // If detail is a string, return it
  if (typeof detail === 'string') return detail
  
  // If detail is an array of validation errors (FastAPI format)
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg || JSON.stringify(e)).join(', ')
  }
  
  // If detail is an object, try to extract message
  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  
  return fallback
}

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

const LOAN_TYPES = [
  'Working Capital',
  'Term Loan',
  'Project Finance',
  'Invoice Discounting',
  'Trade Finance',
  'Equipment Finance',
  'Construction Finance',
  'Bridge Loan',
]

const BUSINESS_MODELS = [
  'B2B',
  'B2C',
  'B2B2C',
  'Marketplace',
  'Hybrid',
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
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Step 1: Entity Details
  const [entityForm, setEntityForm] = useState({
    company_name: '',
    cin: '',
    pan: '',
    sector: '',
    annual_turnover: '',
    date_of_incorporation: '',
    business_model: '',
    employee_count: '',
  })
  const [entityId, setEntityId] = useState(null)
  
  // Step 2: Loan Application
  const [loanForm, setLoanForm] = useState({
    loan_type: '',
    loan_amount: '',
    loan_tenure_months: '',
    expected_interest_rate: '',
    purpose: '',
    collateral_offered: '',
    existing_banking_relationship: false,
  })
  const [applicationId, setApplicationId] = useState(null)
  const [requiredDocs, setRequiredDocs] = useState([])
  
  // Step 3: Company Details (kept for backward compatibility)
  const [form, setForm] = useState({
    company_name: '',
    sector: '',
    loan_amount: '',
    qualitative_notes: '',
  })
  
  // Step 4: Documents
  const [files, setFiles] = useState({})
  const [annualReports, setAnnualReports] = useState([
    { id: 1, file: null, year: 'FY24', label: 'FY 2023-24 (Most Recent)' },
  ])
  
  // Step 5: Qualitative Assessment
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

  // CIN Validation
  const validateCIN = (cin) => {
    const regex = /^[A-Z]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/
    return regex.test(cin)
  }

  // PAN Validation
  const validatePAN = (pan) => {
    const regex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/
    return regex.test(pan)
  }

  // Step 1: Submit Entity Profile
  const handleEntitySubmit = async () => {
    setError('')
    
    if (!entityForm.company_name.trim()) {
      setError('Company name is required')
      return
    }
    if (entityForm.cin && !validateCIN(entityForm.cin)) {
      setError('Invalid CIN format (21 characters: e.g., U12345AB2020PTC123456)')
      return
    }
    if (entityForm.pan && !validatePAN(entityForm.pan)) {
      setError('Invalid PAN format (10 characters: e.g., ABCDE1234F)')
      return
    }
    if (!entityForm.sector) {
      setError('Please select a sector')
      return
    }
    
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/onboarding/entity`, {
        company_name: entityForm.company_name.trim(),
        cin: entityForm.cin || null,
        pan: entityForm.pan || null,
        sector: entityForm.sector,
        annual_turnover: parseFloat(entityForm.annual_turnover) || null,
        date_of_incorporation: entityForm.date_of_incorporation || null,
        business_model: entityForm.business_model || null,
        employee_count: parseInt(entityForm.employee_count) || null,
      })
      
      setEntityId(data.entity_id)
      setCurrentStep(2)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save entity profile'))
    } finally {
      setLoading(false)
    }
  }
  
  // Step 2: Submit Loan Application
  const handleLoanSubmit = async () => {
    setError('')
    
    if (!loanForm.loan_type) {
      setError('Please select loan type')
      return
    }
    if (!loanForm.loan_amount || parseFloat(loanForm.loan_amount) <= 0) {
      setError('Please enter valid loan amount')
      return
    }
    
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/onboarding/loan-application`, {
        entity_id: entityId,
        loan_application: {
          loan_type: loanForm.loan_type,
          loan_amount: parseFloat(loanForm.loan_amount),
          loan_tenure_months: parseInt(loanForm.loan_tenure_months) || null,
          expected_interest_rate: parseFloat(loanForm.expected_interest_rate) || null,
          purpose: loanForm.purpose || null,
          collateral_offered: loanForm.collateral_offered || null,
          existing_banking_relationship: loanForm.existing_banking_relationship,
        },
      })
      
      setApplicationId(data.application_id)
      setRequiredDocs(data.required_documents || [])
      
      // Pre-fill form for backward compatibility
      setForm({
        company_name: entityForm.company_name,
        sector: entityForm.sector,
        loan_amount: loanForm.loan_amount,
        qualitative_notes: '',
      })
      
      setCurrentStep(3)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save loan application'))
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleFile = useCallback((field, file) => {
    setFiles((prev) => ({ ...prev, [field]: file }))
  }, [])

  const addYear = () => {
    const years = ['FY25', 'FY24', 'FY23', 'FY22', 'FY21', 'FY20', 'FY19']
    const usedYears = annualReports.map((r) => r.year)
    const nextYear = years.find((y) => !usedYears.includes(y)) || `FY${Date.now()}`
    setAnnualReports((prev) => [
      ...prev,
      { id: Date.now(), file: null, year: nextYear, label: `${nextYear} Annual Report` },
    ])
  }

  const removeYear = (id) => setAnnualReports((prev) => prev.filter((r) => r.id !== id))

  const updateFile = (id, file) => {
    setAnnualReports((prev) => prev.map((r) => (r.id === id ? { ...r, file } : r)))
  }

  const updateYear = (id, year) => {
    setAnnualReports((prev) => prev.map((r) => (r.id === id ? { ...r, year } : r)))
  }

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

  const handleFinalSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Validation
    if (!applicationId) {
      setError('Application ID missing. Please complete entity and loan details first.')
      return
    }

    const validAnnualReports = annualReports.filter((r) => r.file)
    const otherDocuments = DOC_ZONES
      .filter(({ field }) => field !== 'annual_report')
      .map(({ field }) => ({ file: files[field], type: field }))
      .filter((d) => !!d.file)

    if (validAnnualReports.length === 0) {
      setError('Please upload at least one annual report PDF before proceeding.')
      return
    }

    setLoading(true)

    try {
      const fd = new FormData()
      fd.append('company_name', entityForm.company_name)
      fd.append('sector', entityForm.sector)
      fd.append('loan_amount', loanForm.loan_amount)
      fd.append('loan_type', loanForm.loan_type)

      validAnnualReports.forEach((report) => {
        fd.append('annual_reports', report.file)
        fd.append('annual_report_years', report.year)
      })

      otherDocuments.forEach((doc) => {
        fd.append('documents', doc.file)
        fd.append('document_types', doc.type)
      })

      const { data } = await axios.post(`${API}/appraisal/start`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      navigate(`/appraisal/${data.job_id}/pipeline`)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to start appraisal. Check backend connection.'))
      setLoading(false)
    }
  }

  // Step Navigation
  const goToStep = (step) => {
    if (step <= currentStep || (step === 2 && entityId) || (step === 3 && applicationId)) {
      setCurrentStep(step)
      setError('')
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
        
        {/* Step Progress */}
        <div className="mt-6 flex items-center gap-2">
          {[
            { num: 1, label: 'Entity Details' },
            { num: 2, label: 'Loan Application' },
            { num: 3, label: 'Documents' },
            { num: 4, label: 'Due Diligence' }
          ].map((step, idx) => (
            <div key={step.num} className="flex items-center flex-1">
              <button
                type="button"
                onClick={() => goToStep(step.num)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${ 
                  currentStep === step.num ? 'scale-105' : ''
                } ${
                  currentStep > step.num ? 'cursor-pointer hover:scale-105' : ''
                }`}
                style={{
                  background: currentStep >= step.num ? 'var(--accent)20' : 'var(--surface-elevated)',
                  borderLeft: currentStep === step.num ? '3px solid var(--accent)' : '3px solid transparent',
                }}
                disabled={step.num > currentStep && !(step.num === 2 && entityId) && !(step.num === 3 && applicationId)}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs ${
                  currentStep > step.num ? 'animate-scale-in' : ''
                }`}
                     style={{ 
                       background: currentStep >= step.num ? 'var(--accent)' : 'var(--border)',
                       color: currentStep >= step.num ? 'white' : 'var(--muted)',
                     }}>
                  {currentStep > step.num ? <Check size={14} /> : step.num}
                </div>
                <span className="text-xs font-semibold" style={{ 
                  color: currentStep >= step.num ? 'var(--accent)' : 'var(--muted)' 
                }}>
                  {step.label}
                </span>
              </button>
              {idx < 3 && (
                <div className="flex-1 h-0.5 mx-1" style={{ 
                  background: currentStep > step.num ? 'var(--accent)' : 'var(--border)' 
                }} />
              )}
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={handleFinalSubmit} className="space-y-6">
        {/* STEP 1: Entity Details */}
        {currentStep === 1 && (
          <div className="card p-8 animate-scale-in">
            <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                   style={{ background: 'var(--accent)20', color: 'var(--accent)' }}>
                1
              </div>
              <div>
                <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                  Entity Details
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  Company profile with CIN/PAN validation
                </p>
              </div>
            </div>
            
            <div className="space-y-5">
              <div className="input-group">
                <label className="input-label flex items-center gap-2">
                  <Building2 size={14} style={{ color: 'var(--accent)' }} />
                  Company Name *
                </label>
                <input
                  className="input-field"
                  value={entityForm.company_name}
                  onChange={(e) => setEntityForm({ ...entityForm, company_name: e.target.value })}
                  placeholder="e.g. XYZ Manufacturing Pvt. Ltd."
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-5">
                <div className="input-group">
                  <label className="input-label">
                    Corporate Identification Number (CIN)
                    <span className="text-xs ml-2" style={{ color: 'var(--muted)' }}>21 characters</span>
                  </label>
                  <input
                    className="input-field font-mono"
                    value={entityForm.cin}
                    onChange={(e) => setEntityForm({ ...entityForm, cin: e.target.value.toUpperCase() })}
                    placeholder="U12345AB2020PTC123456"
                    maxLength={21}
                  />
                  {entityForm.cin && !validateCIN(entityForm.cin) && (
                    <p className="text-xs mt-1" style={{ color: 'var(--danger)' }}>
                      Invalid CIN format
                    </p>
                  )}
                </div>

                <div className="input-group">
                  <label className="input-label">
                    PAN
                    <span className="text-xs ml-2" style={{ color: 'var(--muted)' }}>10 characters</span>
                  </label>
                  <input
                    className="input-field font-mono"
                    value={entityForm.pan}
                    onChange={(e) => setEntityForm({ ...entityForm, pan: e.target.value.toUpperCase() })}
                    placeholder="ABCDE1234F"
                    maxLength={10}
                  />
                  {entityForm.pan && !validatePAN(entityForm.pan) && (
                    <p className="text-xs mt-1" style={{ color: 'var(--danger)' }}>
                      Invalid PAN format
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-5">
                <div className="input-group">
                  <label className="input-label flex items-center gap-2">
                    <Layers size={14} style={{ color: 'var(--accent)' }} />
                    Sector *
                  </label>
                  <select
                    className="input-field"
                    value={entityForm.sector}
                    onChange={(e) => setEntityForm({ ...entityForm, sector: e.target.value })}
                    required
                  >
                    <option value="">Select sector...</option>
                    {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>

                <div className="input-group">
                  <label className="input-label flex items-center gap-2">
                    <IndianRupee size={14} style={{ color: 'var(--accent)' }} />
                    Annual Turnover (₹ Crore)
                  </label>
                  <input
                    className="input-field font-mono"
                    type="number"
                    min="0"
                    step="0.01"
                    value={entityForm.annual_turnover}
                    onChange={(e) => setEntityForm({ ...entityForm, annual_turnover: e.target.value })}
                    placeholder="e.g. 25.00"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-5">
                <div className="input-group">
                  <label className="input-label">Date of Incorporation</label>
                  <input
                    type="date"
                    className="input-field"
                    value={entityForm.date_of_incorporation}
                    onChange={(e) => setEntityForm({ ...entityForm, date_of_incorporation: e.target.value })}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Business Model</label>
                  <select
                    className="input-field"
                    value={entityForm.business_model}
                    onChange={(e) => setEntityForm({ ...entityForm, business_model: e.target.value })}
                  >
                    <option value="">Select...</option>
                    {BUSINESS_MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>

              <div className="input-group">
                <label className="input-label">Employee Count</label>
                <input
                  type="number"
                  className="input-field"
                  min="0"
                  value={entityForm.employee_count}
                  onChange={(e) => setEntityForm({ ...entityForm, employee_count: e.target.value })}
                  placeholder="e.g. 150"
                />
              </div>
            </div>

            <div className="flex justify-end mt-8">
              <button
                type="button"
                onClick={handleEntitySubmit}
                disabled={loading}
                className="btn-primary flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="spinner"></div>
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <span>Next: Loan Application</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Loan Application */}
        {currentStep === 2 && (
          <div className="card p-8 animate-scale-in">
            <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                   style={{ background: 'var(--accent2)20', color: 'var(--accent2)' }}>
                2
              </div>
              <div>
                <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                  Loan Application
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  Loan requirements and terms
                </p>
              </div>
            </div>
            
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-5">
                <div className="input-group">
                  <label className="input-label">Loan Type *</label>
                  <select
                    className="input-field"
                    value={loanForm.loan_type}
                    onChange={(e) => setLoanForm({ ...loanForm, loan_type: e.target.value })}
                    required
                  >
                    <option value="">Select loan type...</option>
                    {LOAN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>

                <div className="input-group">
                  <label className="input-label flex items-center gap-2">
                    <IndianRupee size={14} style={{ color: 'var(--accent)' }} />
                    Loan Amount (₹ Crore) *
                  </label>
                  <input
                    className="input-field font-mono"
                    type="number"
                    min="0"
                    step="0.01"
                    value={loanForm.loan_amount}
                    onChange={(e) => setLoanForm({ ...loanForm, loan_amount: e.target.value })}
                    placeholder="e.g. 10.00"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-5">
                <div className="input-group">
                  <label className="input-label">Loan Tenure (Months)</label>
                  <input
                    type="number"
                    className="input-field"
                    min="1"
                    value={loanForm.loan_tenure_months}
                    onChange={(e) => setLoanForm({ ...loanForm, loan_tenure_months: e.target.value })}
                    placeholder="e.g. 60"
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Expected Interest Rate (%)</label>
                  <input
                    type="number"
                    className="input-field font-mono"
                    min="0"
                    step="0.01"
                    value={loanForm.expected_interest_rate}
                    onChange={(e) => setLoanForm({ ...loanForm, expected_interest_rate: e.target.value })}
                    placeholder="e.g. 9.5"
                  />
                </div>
              </div>

              <div className="input-group">
                <label className="input-label">Purpose of Loan</label>
                <textarea
                  className="input-field"
                  rows="3"
                  value={loanForm.purpose}
                  onChange={(e) => setLoanForm({ ...loanForm, purpose: e.target.value })}
                  placeholder="Describe the purpose and intended use of funds..."
                />
              </div>

              <div className="input-group">
                <label className="input-label">Collateral Offered</label>
                <input
                  className="input-field"
                  value={loanForm.collateral_offered}
                  onChange={(e) => setLoanForm({ ...loanForm, collateral_offered: e.target.value })}
                  placeholder="e.g. Property, Equipment, Receivables"
                />
              </div>

              <div className="input-group">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4"
                    checked={loanForm.existing_banking_relationship}
                    onChange={(e) => setLoanForm({ ...loanForm, existing_banking_relationship: e.target.checked })}
                  />
                  <span className="text-sm" style={{ color: 'var(--text)' }}>
                    Existing banking relationship with your institution
                  </span>
                </label>
              </div>
            </div>

            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className="btn-secondary flex items-center gap-2"
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button
                type="button"
                onClick={handleLoanSubmit}
                disabled={loading}
                className="btn-primary flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="spinner"></div>
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <span>Next: Documents</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Document Upload */}
        {currentStep === 3 && (
          <div className="card p-8 animate-scale-in">
            <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                   style={{ background: 'var(--success)20', color: 'var(--success)' }}>
                3
              </div>
              <div>
                <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                  Financial Documents
                </h2>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  Upload required documents • Max 50MB per file • PDF preferred
                </p>
              </div>
            </div>

            {/* Required Documents Alert */}
            {requiredDocs.length > 0 && (
              <div className="mb-6 p-4 rounded-lg" 
                   style={{ background: 'var(--accent)10', border: '1px solid var(--accent)30' }}>
                <div className="flex items-start gap-3">
                  <AlertCircle size={18} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <p className="text-sm font-semibold mb-2" style={{ color: 'var(--text)' }}>
                      Required Documents for {loanForm.loan_type}
                    </p>
                    <ul className="text-xs space-y-1" style={{ color: 'var(--text)' }}>
                      {requiredDocs.map((doc, idx) => (
                        <li key={idx}>• {doc}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2" style={{ marginBottom: 8 }}>
                <label style={{ color: '#D8EAF2', fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 12 }}>
                  Annual Reports
                  <span style={{ color: '#7A9BB5', fontWeight: 400, marginLeft: 8 }}>
                    (Upload 1-5 years for trend analysis)
                  </span>
                </label>

                {annualReports.map((report) => (
                  <div
                    key={report.id}
                    style={{
                      display: 'flex', gap: 12, alignItems: 'center', marginBottom: 10,
                      background: '#0F2640', borderRadius: 8, padding: '10px 14px',
                      border: report.file ? '1px solid #00C2A8' : '1px solid #1E3A5F'
                    }}
                  >
                    <select
                      value={report.year}
                      onChange={(e) => updateYear(report.id, e.target.value)}
                      style={{
                        background: '#0B1D35', color: 'white', border: '1px solid #1E3A5F',
                        borderRadius: 6, padding: '6px 10px', fontSize: 13, width: 100
                      }}
                    >
                      {['FY25', 'FY24', 'FY23', 'FY22', 'FY21', 'FY20', 'FY19'].map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>

                    <label style={{ flex: 1, cursor: 'pointer' }}>
                      <input
                        type="file"
                        accept=".pdf"
                        style={{ display: 'none' }}
                        onChange={(e) => updateFile(report.id, e.target.files?.[0])}
                      />
                      <div
                        style={{
                          padding: '8px 12px', borderRadius: 6, fontSize: 13,
                          background: '#071528', border: '1px dashed #1E3A5F',
                          color: report.file ? '#00C2A8' : '#7A9BB5'
                        }}
                      >
                        {report.file ? `✓ ${report.file.name}` : '+ Click to upload PDF'}
                      </div>
                    </label>

                    {annualReports.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeYear(report.id)}
                        style={{ background: 'none', border: 'none', color: '#EF4444', cursor: 'pointer', fontSize: 18 }}
                      >
                        x
                      </button>
                    )}
                  </div>
                ))}

                {annualReports.length < 5 && (
                  <button
                    type="button"
                    onClick={addYear}
                    style={{
                      background: 'none', border: '1px dashed #1E3A5F', borderRadius: 8,
                      color: '#7A9BB5', padding: '8px 16px', cursor: 'pointer', fontSize: 13,
                      width: '100%', marginTop: 4
                    }}
                  >
                    + Add another year (up to {5 - annualReports.length} more)
                  </button>
                )}
              </div>

              {DOC_ZONES.filter((meta) => meta.field !== 'annual_report').map((meta, idx) => (
                <div key={meta.field} className="animate-slide-up" style={{ animationDelay: `${idx * 50}ms` }}>
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
                    {annualReports.filter((r) => !!r.file).length + Object.values(files).filter(Boolean).length} files uploaded
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                    {annualReports.filter((r) => !!r.file).length + Object.values(files).filter(Boolean).length === 0 
                      ? 'Upload documents for better analysis accuracy'
                      : 'Engine will process all uploaded documents'
                    }
                  </p>
                </div>
              </div>
              {annualReports.filter((r) => !!r.file).length + Object.values(files).filter(Boolean).length > 0 && (
                <div className="px-3 py-1.5 rounded-full font-mono text-xs font-semibold"
                     style={{ background: 'var(--accent)15', color: 'var(--accent)' }}>
                  Ready
                </div>
              )}
            </div>

            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="btn-secondary flex items-center gap-2"
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button
                type="button"
                onClick={() => setCurrentStep(4)}
                className="btn-primary flex items-center gap-2"
              >
                <span>Next: Due Diligence</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: Primary Due Diligence */}
        {currentStep === 4 && (
          <div className="card p-8 animate-scale-in">
            <div className="flex items-center gap-3 mb-6 pb-5 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                   style={{ background: 'var(--warning)20', color: 'var(--warning)' }}>
                4
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

            <div className="flex justify-between mt-8">
              <button
                type="button"
                onClick={() => setCurrentStep(3)}
                className="btn-secondary flex items-center gap-2"
              >
                <ArrowLeft size={16} />
                <span>Back</span>
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
          </div>
        )}

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
                  {currentStep < 3 ? 'Validation Error' : 'Submission Error'}
                </p>
                <p className="text-xs" style={{ color: 'var(--danger-dark)' }}>
                  {error}
                </p>
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
