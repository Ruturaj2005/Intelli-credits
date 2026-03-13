/**
 * SchemaSelection - Configure extraction schemas for classified documents
 * Allows users to select which schema template to use for each document
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import {
  Settings,
  ChevronDown,
  ChevronRight,
  Info,
  Check,
  FileText,
  Edit3,
  Plus,
  X,
  ArrowRight,
  Shield,
} from 'lucide-react'

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

// Format schema field count
const formatFieldCount = (count) => {
  return `${count} field${count !== 1 ? 's' : ''}`
}

export default function SchemaSelection() {
  const navigate = useNavigate()
  const { applicationId } = useParams()
  
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  
  // Data from classification review
  const [classificationData, setClassificationData] = useState(null)
  const [qualitativeInputs, setQualitativeInputs] = useState(null)
  
  // Schema data
  const [allSchemas, setAllSchemas] = useState([])
  const [recommendedSchemas, setRecommendedSchemas] = useState({}) // file_id -> schemas[]
  const [selectedSchemas, setSelectedSchemas] = useState({}) // file_id -> schema_id
  
  // UI state
  const [expandedDocs, setExpandedDocs] = useState({}) // file_id -> boolean
  const [advancedMode, setAdvancedMode] = useState({}) // file_id -> boolean
  const [customHints, setCustomHints] = useState({}) // file_id -> { field_name -> hints[] }

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        // Get classification data from navigation state
        const state = history.state?.usr
        if (!state || !state.classificationData) {
          setError('No classification data found. Please start from document upload.')
          setLoading(false)
          return
        }
        
        setClassificationData(state.classificationData)
        setQualitativeInputs(state.qualitativeInputs)

        // Load all schemas
        const { data: schemaList } = await axios.get(`${API}/schemas/list`)
        setAllSchemas(schemaList.schemas)

        // Get recommendations for each document
        const recommendations = {}
        const defaults = {}
        
        for (const doc of state.classificationData.detected_documents) {
          const docType = state.userOverrides?.[doc.file_id] || doc.auto_classification
          
          try {
            const { data: recData } = await axios.get(
              `${API}/schemas/recommend?document_type=${docType}`
            )
            recommendations[doc.file_id] = recData.recommendations
            
            // Default to first recommendation
            if (recData.recommendations.length > 0) {
              defaults[doc.file_id] = recData.recommendations[0].template_id
            }
          } catch (err) {
            console.error(`Failed to get recommendations for ${doc.file_id}:`, err)
            recommendations[doc.file_id] = []
          }
        }
        
        setRecommendedSchemas(recommendations)
        setSelectedSchemas(defaults)
        setLoading(false)
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to load schema templates'))
        setLoading(false)
      }
    }
    
    loadData()
  }, [applicationId])

  // Toggle document expansion
  const toggleExpand = (fileId) => {
    setExpandedDocs((prev) => ({ ...prev, [fileId]: !prev[fileId] }))
  }

  // Toggle advanced mode for document
  const toggleAdvancedMode = (fileId) => {
    setAdvancedMode((prev) => ({ ...prev, [fileId]: !prev[fileId] }))
  }

  // Change selected schema
  const handleSchemaChange = (fileId, schemaId) => {
    setSelectedSchemas((prev) => ({ ...prev, [fileId]: schemaId }))
  }

  // Add custom hint for a field
  const handleAddHint = (fileId, fieldName, hint) => {
    if (!hint.trim()) return
    
    setCustomHints((prev) => ({
      ...prev,
      [fileId]: {
        ...(prev[fileId] || {}),
        [fieldName]: [...(prev[fileId]?.[fieldName] || []), hint.trim()],
      },
    }))
  }

  // Remove custom hint
  const handleRemoveHint = (fileId, fieldName, idx) => {
    setCustomHints((prev) => {
      const fileHints = { ...prev[fileId] }
      fileHints[fieldName] = fileHints[fieldName].filter((_, i) => i !== idx)
      return { ...prev, [fileId]: fileHints }
    })
  }

  // Get schema by ID
  const getSchemaById = (schemaId) => {
    return allSchemas.find((s) => s.template_id === schemaId)
  }

  // Submit schema selections
  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')

    try {
      // Build schema mapping payload
      const documentSchemaMapping = Object.entries(selectedSchemas).map(([fileId, schemaId]) => ({
        file_id: fileId,
        selected_schema_id: schemaId,
        custom_hints: customHints[fileId] || null,
      }))

      // Save schema selections
      await axios.post(`${API}/schemas/select`, {
        application_id: applicationId,
        document_schema_mapping: documentSchemaMapping,
      })

      // Now trigger the pipeline with classifications
      const classifications = classificationData.detected_documents.map((doc) => ({
        file_id: doc.file_id,
        confirmed_type: doc.auto_classification, // Already confirmed in previous step
        user_modified: false,
        user_comment: null,
      }))

      const { data } = await axios.post(`${API}/documents/confirm-classification`, {
        application_id: applicationId,
        classifications,
        qualitative_inputs: qualitativeInputs,
      })

      // Redirect to pipeline
      navigate(`/appraisal/${data.job_id}/pipeline`)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to save schema configuration'))
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-10">
        <div className="flex items-center justify-center h-64">
          <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
        </div>
      </div>
    )
  }

  if (error && !classificationData) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-10">
        <div className="card p-8">
          <p className="text-center" style={{ color: 'var(--danger)' }}>
            {error}
          </p>
          <div className="flex justify-center mt-6">
            <button onClick={() => navigate('/dashboard')} className="btn-secondary">
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  const docsWithSchemas = classificationData?.detected_documents || []

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      {/* Header */}
      <div className="mb-10 animate-slide-up">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-dark))' }}
          >
            <Settings size={24} color="white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-syne font-bold text-3xl" style={{ color: 'var(--text)' }}>
              Configure Extraction Schemas
            </h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--muted)' }}>
              Choose which data fields to extract from each document. Advanced mode allows custom hints.
            </p>
          </div>
        </div>

        {/* Innovation Badge */}
        <div
          className="mt-6 p-4 rounded-lg flex items-start gap-3 border"
          style={{
            background: 'var(--accent)10',
            borderColor: 'var(--accent)',
          }}
        >
          <Shield size={20} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text)' }}>
              Configurable Schema Templates
            </p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Define exactly which fields to extract from each document type. Our pre-built templates
              cover financial analysis, borrowing details, ownership structure, portfolio risk, and ALM metrics.
            </p>
          </div>
        </div>
      </div>

      {/* Document Schema Configuration */}
      <div className="space-y-4 mb-8">
        {docsWithSchemas.map((doc, idx) => {
          const selectedSchemaId = selectedSchemas[doc.file_id]
          const selectedSchema = getSchemaById(selectedSchemaId)
          const recommendations = recommendedSchemas[doc.file_id] || []
          const isExpanded = expandedDocs[doc.file_id]
          const isAdvanced = advancedMode[doc.file_id]

          return (
            <div
              key={doc.file_id}
              className="card p-6 animate-scale-in"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              {/* Document Header */}
              <div className="flex items-center gap-4 mb-4">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: 'var(--surface-elevated)' }}
                >
                  <FileText size={18} style={{ color: 'var(--accent)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: 'var(--text)' }}>
                    {doc.file_name}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>
                    Type: {doc.auto_classification.replace(/_/g, ' ')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => toggleExpand(doc.file_id)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown size={18} style={{ color: 'var(--muted)' }} />
                  ) : (
                    <ChevronRight size={18} style={{ color: 'var(--muted)' }} />
                  )}
                </button>
              </div>

              {/* Schema Selection */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="input-label text-xs mb-2">Selected Schema Template</label>
                  <select
                    className="input-field text-sm"
                    value={selectedSchemaId || ''}
                    onChange={(e) => handleSchemaChange(doc.file_id, e.target.value)}
                  >
                    {recommendations.length > 0 ? (
                      <>
                        <optgroup label="Recommended">
                          {recommendations.map((schema) => (
                            <option key={schema.template_id} value={schema.template_id}>
                              {schema.template_name} ({formatFieldCount(schema.field_count)})
                            </option>
                          ))}
                        </optgroup>
                        <optgroup label="Other Schemas">
                          {allSchemas
                            .filter(
                              (s) => !recommendations.some((r) => r.template_id === s.template_id)
                            )
                            .map((schema) => (
                              <option key={schema.template_id} value={schema.template_id}>
                                {schema.template_name} ({formatFieldCount(schema.field_count)})
                              </option>
                            ))}
                        </optgroup>
                      </>
                    ) : (
                      allSchemas.map((schema) => (
                        <option key={schema.template_id} value={schema.template_id}>
                          {schema.template_name} ({formatFieldCount(schema.field_count)})
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div className="flex flex-col justify-end">
                  <button
                    type="button"
                    onClick={() => toggleAdvancedMode(doc.file_id)}
                    className={`btn-${isAdvanced ? 'primary' : 'secondary'} text-sm flex items-center justify-center gap-2`}
                  >
                    <Edit3 size={14} />
                    <span>{isAdvanced ? 'Advanced Mode Active' : 'Enable Advanced Mode'}</span>
                  </button>
                </div>
              </div>

              {/* Schema Info */}
              {selectedSchema && (
                <div
                  className="p-3 rounded-lg flex items-start gap-2 mb-4"
                  style={{ background: 'var(--surface-elevated)' }}
                >
                  <Info size={16} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>
                    {selectedSchema.description}
                  </p>
                </div>
              )}

              {/* Expanded: Show fields */}
              {isExpanded && selectedSchema && (
                <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                  <p className="text-xs font-semibold mb-3" style={{ color: 'var(--muted)' }}>
                    Extraction Fields ({selectedSchema.field_count}):
                  </p>
                  <div className="space-y-3">
                    {selectedSchema.fields.map((field) => (
                      <div
                        key={field.field_name}
                        className="p-3 rounded-lg"
                        style={{ background: 'var(--bg-secondary)' }}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                              {field.field_label}
                            </p>
                            {field.required && (
                              <span
                                className="px-2 py-0.5 rounded text-xs font-semibold"
                                style={{ background: 'var(--danger)20', color: 'var(--danger)' }}
                              >
                                Required
                              </span>
                            )}
                            <span
                              className="px-2 py-0.5 rounded text-xs font-mono"
                              style={{ background: 'var(--accent)10', color: 'var(--accent)' }}
                            >
                              {field.data_type}
                            </span>
                          </div>
                        </div>
                        
                        <p className="text-xs mb-2" style={{ color: 'var(--muted)' }}>
                          {field.description}
                        </p>

                        <div className="flex flex-wrap gap-1 mb-2">
                          {field.extraction_hints.map((hint, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 rounded text-xs"
                              style={{ background: 'var(--surface-elevated)', color: 'var(--text)' }}
                            >
                              {hint}
                            </span>
                          ))}
                        </div>

                        {/* Advanced Mode: Custom Hints */}
                        {isAdvanced && (
                          <div className="mt-3">
                            <label className="input-label text-xs mb-1">Custom Hints</label>
                            <div className="flex gap-2 mb-2">
                              <input
                                type="text"
                                className="input-field text-xs flex-1"
                                placeholder="Add custom keyword hint..."
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    handleAddHint(doc.file_id, field.field_name, e.target.value)
                                    e.target.value = ''
                                  }
                                }}
                              />
                              <button
                                type="button"
                                onClick={(e) => {
                                  const input = e.target.previousSibling
                                  handleAddHint(doc.file_id, field.field_name, input.value)
                                  input.value = ''
                                }}
                                className="btn-secondary text-xs px-3"
                              >
                                <Plus size={14} />
                              </button>
                            </div>
                            
                            {/* Display custom hints */}
                            {customHints[doc.file_id]?.[field.field_name]?.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {customHints[doc.file_id][field.field_name].map((hint, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 rounded text-xs flex items-center gap-1"
                                    style={{ background: 'var(--accent2)20', color: 'var(--accent2)' }}
                                  >
                                    {hint}
                                    <button
                                      type="button"
                                      onClick={() => handleRemoveHint(doc.file_id, field.field_name, idx)}
                                      className="hover:opacity-70"
                                    >
                                      <X size={12} />
                                    </button>
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="card p-5 border-2 animate-scale-in mb-8"
          style={{ borderColor: 'var(--danger)', background: 'var(--danger)10' }}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: 'var(--danger)20' }}
            >
              <span style={{ color: 'var(--danger)' }}>!</span>
            </div>
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: 'var(--danger)' }}>
                Configuration Error
              </p>
              <p className="text-xs" style={{ color: 'var(--danger-dark)' }}>
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div
        className="card p-5 mb-8 border"
        style={{ borderColor: 'var(--success)', background: 'var(--success)05' }}
      >
        <div className="flex items-center gap-3">
          <Check size={24} style={{ color: 'var(--success)' }} />
          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
              {Object.keys(selectedSchemas).length} document{Object.keys(selectedSchemas).length !== 1 ? 's' : ''} configured
            </p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              {Object.keys(advancedMode).filter((id) => advancedMode[id]).length} in advanced mode with custom hints
            </p>
          </div>
        </div>
      </div>

      {/* CTA Buttons */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="btn-secondary"
        >
          ← Back to Classification
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting || Object.keys(selectedSchemas).length === 0}
          className="btn-primary flex items-center gap-3 px-10"
        >
          {submitting ? (
            <>
              <div className="spinner"></div>
              <span>Configuring & Starting...</span>
            </>
          ) : (
            <>
              <span>Confirm Schemas & Start Analysis</span>
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </div>
    </div>
  )
}
