/**
 * VeriFin - Multi-Tenant Database Middleware
 * Dynamically resolves tenant database and scopes operations
 */

const mongoose = require('mongoose');

// Cache of initialized tenant models to prevent recompilation errors
const tenantModelCache = new Map();

/**
 * Returns formatted tenant database name
 */
const getTenantDbName = (companyId) => {
  const cleanId = (companyId || 'comp_default').replace(/[^a-zA-Z0-9_-]/g, '_');
  return `verifin_tenant_${cleanId}`;
};

/**
 * Get tenant-scoped Mongoose model
 */
const getTenantModel = (companyId, modelName, schema) => {
  const dbName = getTenantDbName(companyId);
  const cacheKey = `${dbName}:${modelName}`;

  if (tenantModelCache.has(cacheKey)) {
    return tenantModelCache.get(cacheKey);
  }

  // Switch to tenant-specific database
  const tenantDb = mongoose.connection.useDb(dbName, { useCache: true });
  const model = tenantDb.model(modelName, schema);
  tenantModelCache.set(cacheKey, model);
  return model;
};

/**
 * Express middleware to attach tenant context and scoped DB helpers
 */
const tenantContextMiddleware = (req, res, next) => {
  const companyId = req.headers['x-company-id'] || (req.user && req.user.companyId) || 'comp_default';
  const projectId = req.headers['x-project-id'] || (req.user && req.user.activeProjectId) || 'proj_default';

  req.companyId = companyId;
  req.projectId = projectId;
  req.tenantDbName = getTenantDbName(companyId);

  req.getTenantModel = (modelName, schema) => {
    return getTenantModel(companyId, modelName, schema);
  };

  next();
};

module.exports = {
  getTenantDbName,
  getTenantModel,
  tenantContextMiddleware
};
