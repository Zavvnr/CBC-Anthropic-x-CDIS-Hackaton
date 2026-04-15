
# Sample: User Authentication Service

## Overview
A simple authentication service that validates user credentials and manages login sessions.

## Code

### 1. File Header
```javascript
/**
 * @file auth-service.js - Handles user authentication and session management
 * @author Zavier
 * @date 2026-04-13
 */
```

### 2. Imports/Requires
```javascript
// External dependencies
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';

// Internal modules
import { UserRepository } from './repositories/user-repository';
import { SessionStore } from './stores/session-store';
```

### 3. Constants
```javascript
const MAX_LOGIN_ATTEMPTS = 5;
const TOKEN_EXPIRY_SECONDS = 3600;
const BCRYPT_SALT_ROUNDS = 12;
```

### 4. Function Template
```javascript
/**
 * Verifies a plain-text password against a stored hash
 * @param {string} plainPassword - The password entered by the user
 * @param {string} hashedPassword - The bcrypt hash stored in the database
 * @returns {Promise<boolean>} True if the password matches, false otherwise
 */
async function verifyPassword(plainPassword, hashedPassword) {
    // bcrypt handles timing-safe comparison internally
    return bcrypt.compare(plainPassword, hashedPassword);
}

/**
 * Generates a signed JWT for an authenticated user
 * @param {Object} user - User object containing id and role
 * @param {string} secret - The signing secret from environment config
 * @returns {string} Signed JWT token
 */
function generateToken(user, secret) {
    return jwt.sign(
        { userId: user.id, role: user.role },
        secret,
        { expiresIn: TOKEN_EXPIRY_SECONDS }
    );
}
```

### 5. Class Template
```javascript
class AuthService {
    /**
     * Creates an AuthService instance
     * @param {Object} config - Configuration containing jwtSecret
     */
    constructor(config) {
        this.jwtSecret = config.jwtSecret;
        this.userRepo = new UserRepository();
        this.sessionStore = new SessionStore();
    }

    /**
     * Authenticates a user and returns a session token
     * @param {string} email - The user's email address
     * @param {string} password - The user's plain-text password
     * @returns {Promise<string>} JWT token on success
     * @throws {Error} If credentials are invalid or account is locked
     */
    async login(email, password) {
        const user = await this.userRepo.findByEmail(email);

        if (!user) {
            // Avoid leaking whether the email exists
            throw new Error('Invalid credentials');
        }

        if (user.loginAttempts >= MAX_LOGIN_ATTEMPTS) {
            throw new Error('Account locked due to too many failed attempts');
        }

        const isValid = await verifyPassword(password, user.hashedPassword);

        if (!isValid) {
            await this.userRepo.incrementLoginAttempts(user.id);
            throw new Error('Invalid credentials');
        }

        // Reset failed attempts on successful login
        await this.userRepo.resetLoginAttempts(user.id);

        const token = generateToken(user, this.jwtSecret);
        await this.sessionStore.save(user.id, token);

        return token;
    }

    // Invalidates all active sessions for the given user
    async logout(userId) {
        await this.sessionStore.deleteAll(userId);
    }
}
```

## Best Practices Demonstrated
- `verifyPassword` and `generateToken` are small, single-purpose functions
- Constants replace magic numbers (`MAX_LOGIN_ATTEMPTS`, `TOKEN_EXPIRY_SECONDS`)
- Comments explain *why* (e.g., avoiding email enumeration, timing-safe comparison) rather than *what*
- Class methods delegate to focused helpers instead of containing all logic inline
- Consistent 4-space indentation throughout


## Notes
- This sample is in JavaScript; equivalent patterns in Python would use `dataclasses`, type hints, and `async`/`await` with `asyncio`, following PEP 8 conventions.
