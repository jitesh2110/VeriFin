const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const User = require('./models/User');

// JWT Secret (in production, use environment variable)
const JWT_SECRET = process.env.JWT_SECRET || 'verifin-secret-key-2025';

// Helper to create token with multi-tenant claims
const createTenantToken = (user) => {
  return jwt.sign(
    {
      id: user._id,
      userId: user._id,
      username: user.username,
      email: user.email,
      role: user.role,
      companyId: user.companyId || 'comp_default',
      companyName: user.companyName || 'Default Enterprise',
      assignedProjects: user.assignedProjects || [],
      activeProjectId: user.activeProjectId || 'proj_default'
    },
    JWT_SECRET,
    { expiresIn: '7d' }
  );
};

// Middleware to verify JWT token
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ success: false, message: 'Access token required' });
  }

  jwt.verify(token, JWT_SECRET, (err, decoded) => {
    if (err) {
      return res.status(403).json({ success: false, message: 'Invalid or expired token' });
    }
    req.user = decoded;
    req.companyId = decoded.companyId || 'comp_default';
    req.projectId = decoded.activeProjectId || 'proj_default';
    next();
  });
};

// POST /api/auth/signup - Register new user
router.post('/signup', async (req, res) => {
  try {
    const { username, email, password, role, companyId, companyName, assignedProjects, activeProjectId } = req.body;

    // Validation
    if (!username || !email || !password) {
      return res.status(400).json({
        success: false,
        message: 'Username, email, and password are required'
      });
    }

    // Check if user already exists
    const existingUser = await User.findOne({ $or: [{ email }, { username }] });
    if (existingUser) {
      return res.status(400).json({
        success: false,
        message: 'User with this email or username already exists'
      });
    }

    // Create new user with tenant details
    const user = new User({
      username,
      email,
      password,
      role: role || 'user',
      companyId: companyId || 'comp_default',
      companyName: companyName || 'Default Enterprise',
      assignedProjects: assignedProjects || [{ projectId: 'proj_default', projectName: 'Default Project', role: 'member' }],
      activeProjectId: activeProjectId || 'proj_default'
    });

    await user.save();

    // Generate JWT token with tenant claims
    const token = createTenantToken(user);

    res.status(201).json({
      success: true,
      message: 'User registered successfully',
      token,
      user: {
        id: user._id,
        username: user.username,
        email: user.email,
        role: user.role,
        companyId: user.companyId,
        companyName: user.companyName,
        assignedProjects: user.assignedProjects,
        activeProjectId: user.activeProjectId
      }
    });
  } catch (error) {
    console.error('Signup error:', error);
    res.status(500).json({
      success: false,
      message: 'Error creating user',
      error: error.message
    });
  }
});

// POST /api/auth/login - Login user
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validation
    if (!email || !password) {
      return res.status(400).json({
        success: false,
        message: 'Email and password are required'
      });
    }

    // Find user
    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Check password
    const isPasswordValid = await user.comparePassword(password);
    if (!isPasswordValid) {
      return res.status(401).json({
        success: false,
        message: 'Invalid email or password'
      });
    }

    // Update last login
    user.lastLogin = new Date();
    await user.save();

    // Generate JWT token with tenant claims
    const token = createTenantToken(user);

    res.json({
      success: true,
      message: 'Login successful',
      token,
      user: {
        id: user._id,
        username: user.username,
        email: user.email,
        role: user.role,
        companyId: user.companyId || 'comp_default',
        companyName: user.companyName || 'Default Enterprise',
        assignedProjects: user.assignedProjects || [],
        activeProjectId: user.activeProjectId || 'proj_default',
        lastLogin: user.lastLogin
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      success: false,
      message: 'Error during login',
      error: error.message
    });
  }
});

// GET /api/auth/verify - Verify JWT token
router.get('/verify', authenticateToken, async (req, res) => {
  try {
    const user = await User.findById(req.user.id || req.user.userId).select('-password');
    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'User not found'
      });
    }

    res.json({
      success: true,
      user: {
        id: user._id,
        username: user.username,
        email: user.email,
        role: user.role,
        companyId: user.companyId || 'comp_default',
        companyName: user.companyName || 'Default Enterprise',
        assignedProjects: user.assignedProjects || [],
        activeProjectId: user.activeProjectId || 'proj_default',
        lastLogin: user.lastLogin
      }
    });
  } catch (error) {
    console.error('Verify error:', error);
    res.status(500).json({
      success: false,
      message: 'Error verifying token',
      error: error.message
    });
  }
});

// GET /api/auth/me - Get current user
router.get('/me', authenticateToken, async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select('-password');
    res.json({
      success: true,
      user
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Error fetching user',
      error: error.message
    });
  }
});

module.exports = { router, authenticateToken };
