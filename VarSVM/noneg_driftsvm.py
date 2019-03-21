import numpy as np
from scipy import sparse

class noneg_driftsvm(object):
	## the function use coordinate descent to update the drift linear SVM
	## C \sum_{i=1}^n w_i V(y_i(\beta^T x_i + drift_i)) + 1/2 \beta^T \beta
	def __init__(self, C=1., print_step=True, eps=1e-4):
		self.loss = 'hinge'
		self.alpha = []
		self.beta = []
		self.rho = []
		self.C = C
		self.max_iter = 1000
		self.eps = eps
		self.print_step = print_step

	def fit(self, X, y, drift, sample_weight=1.):
		n, d = X.shape
		self.alpha, self.rho = np.zeros(n), np.zeros(d)
		diff = 1.
		drift = drift * y
		sample_weight = self.C*np.array(sample_weight)
		sample_weight = sample_weight * np.ones(n)
		## compute Xy matrix
		if sparse.issparse(X):
			Xy = sparse.csr_matrix(X.multiply(y.reshape(-1, 1)))
		else:
			Xy = X * y[:, np.newaxis]
		## compute diag vector
		if sparse.issparse(X):
			diag = np.array([Xy[i].dot(Xy[i]) for i in range(n)])
		else:
			diag = np.array([Xy[i].dot(Xy[i]) for i in range(n)])

		self.beta = np.dot(self.alpha, Xy) + self.rho
		# coordinate descent
		for ite in range(self.max_iter):
			if diff < self.eps:
				break
			beta_old = np.copy(self.beta)
			for i in range(n):
				delta_tmp = (1. - drift[i] - np.dot(self.beta, Xy[i])) / diag[i]
				delta_tmp = max(-self.alpha[i], min(sample_weight[i] - self.alpha[i], delta_tmp))
				self.alpha[i] = self.alpha[i] + delta_tmp
				self.beta = self.beta + delta_tmp*Xy[i]
			for j in range(d):
				delta_tmp = max(-self.rho[j], -self.beta[j])
				self.rho[j] = self.rho[j] + delta_tmp
				self.beta[j] = self.beta[j] + delta_tmp
			obj = self.dual_obj(Xy=Xy, drift=drift)
			# obj = self.prime_obj(X=X, y=y, drift=drift)
			diff = np.sum(np.abs(beta_old - self.beta))/np.sum(np.abs(beta_old+1e-10))
			if self.print_step:
				if ite > 0:
					print("ite %s coordinate descent with diff: %.3f; obj: %.3f" %(ite, diff, obj))
	
	# def prime_obj(self, X, y, drift):
	# 	n, d = X.shape
	# 	score = self.decision_function(X=X, drift=drift)
	# 	obj = n*hinge_loss(y, score) + .5 * np.dot(self.beta, self.beta)
	# 	return obj

	def dual_obj(self, Xy, drift):
		sum_tmp = np.dot(self.alpha, Xy)
		obj = np.dot(1. - drift, self.alpha) - .5 * np.dot(sum_tmp, sum_tmp) \
			- .5 * np.dot(self.rho, self.rho) - np.dot(sum_tmp, self.rho)
		return obj

	def decision_function(self, X, drift):
		return np.dot(X, self.beta) + drift
