const mongoose = require('mongoose');
const User = require('./models/User');
require('dotenv').config();

// MongoDB connection
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/verifin';

async function createDemoUsers() {
  try {
    await mongoose.connect(MONGODB_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true
    });

    console.log('✅ Connected to MongoDB');

    // Delete existing demo users
    await User.deleteMany({ email: { $in: ['admin@verifin.ai', 'user@verifin.ai', 'admin@fintel.ai', 'user@fintel.ai'] } });
    console.log('🗑️  Cleared existing demo users');

    // Create Admin User (TechCorp)
    const admin = new User({
      username: 'admin',
      email: 'admin@verifin.ai',
      password: 'admin123',
      role: 'admin',
      companyId: 'comp_techcorp',
      companyName: 'TechCorp Logistics',
      assignedProjects: [
        { projectId: 'proj_fleet', projectName: 'Fleet Operations', role: 'admin' },
        { projectId: 'proj_supply', projectName: 'Supply Chain', role: 'admin' }
      ],
      activeProjectId: 'proj_fleet'
    });
    await admin.save();
    console.log('✅ Admin user created');
    console.log('   Email: admin@verifin.ai');
    console.log('   Company: TechCorp Logistics (comp_techcorp)');
    console.log('   Role: admin');

    // Create Demo User (Global Retail)
    const user = new User({
      username: 'demouser',
      email: 'user@verifin.ai',
      password: 'user123',
      role: 'user',
      companyId: 'comp_globalretail',
      companyName: 'Global Retail Corp',
      assignedProjects: [
        { projectId: 'proj_procure', projectName: 'Store Procurement', role: 'member' }
      ],
      activeProjectId: 'proj_procure'
    });
    await user.save();
    console.log('✅ Demo user created');
    console.log('   Email: user@verifin.ai');
    console.log('   Company: Global Retail Corp (comp_globalretail)');
    console.log('   Role: user');

    console.log('\n🎉 Demo users created successfully!');
    console.log('\n📋 DEMO CREDENTIALS:');
    console.log('='.repeat(50));
    console.log('\nADMIN LOGIN:');
    console.log('  Email: admin@verifin.ai');
    console.log('  Password: admin123');
    console.log('\nUSER LOGIN:');
    console.log('  Email: user@verifin.ai');
    console.log('  Password: user123');
    console.log('='.repeat(50));

    await mongoose.connection.close();
    console.log('\n✅ Database connection closed');
  } catch (error) {
    console.error('❌ Error creating demo users:', error);
  }
}

createDemoUsers();
