import numpy as np
from scipy import sparse
from VarSVM import CD_drift

class driftsvm(object):
	## the function use coordinate descent to update the drift linear SVM
	## C \sum_{i=1}^n w_i V(y_i(\beta^T x_i + drift_i)) + 1/2 \beta^T \beta
	def __init__(self, C=1., loss='hinge', print_step=1, eps=1e-4):
		self.loss = loss
		self.alpha = []
		self.beta = []
		self.C = C
		self.max_iter = 1000
		self.eps = eps
		self.print_step = print_step

	def fit(self, X, y, drift, sample_weight=1.):
		n, d = X.shape
		self.alpha = np.zeros(n)
		diff = 1.
		sample_weight = self.C*np.array(sample_weight)
		sample_weight = sample_weight * np.ones(n)
		drift = y * drift
		## compute Xy matrix
		if sparse.issparse(X):
			Xy = sparse.csr_matrix(X.multiply(y.reshape(-1, 1)))
		else:
			Xy = X * y[:, np.newaxis]
		## compute diag vector
		if sparse.issparse(X):
			diag = np.array([Xy[i].dot(Xy[i].T).toarray()[0][0] for i in range(n)])
		else:
			diag = np.array([Xy[i].dot(Xy[i]) for i in range(n)])

		self.beta = Xy.T.dot(self.alpha)
		# coordinate descent
		if sparse.issparse(Xy):
			for ite in range(self.max_iter):
				if diff < self.eps:
					break
				beta_old = np.copy(self.beta)
				for i in range(n):
					if diag[i] != 0:
						delta_tmp = (1. - drift[i] - Xy[i].dot(self.beta)[0]) / diag[i]
						delta_tmp = max(-self.alpha[i], min(sample_weight[i] - self.alpha[i], delta_tmp))
					if diag[i] == 0:
						if Xy[i].dot(self.beta)[0] < 1 - drift[i]:
							delta_tmp = sample_weight[i] - self.alpha[i]
						else:
							delta_tmp = -self.alpha[i]
					self.alpha[i] = self.alpha[i] + delta_tmp
					self.beta = np.array(self.beta + delta_tmp*Xy[i])[0]
				diff = np.sum(np.abs(beta_old - self.beta))/np.sum(np.abs(beta_old+1e-10))
				if self.print_step == 1:
					if ite > 0:
						print("ite %s coordinate descent with diff: %.3f;" %(ite, diff))
		else:
			alpha_C, beta_C = CD_drift(Xy, diag, drift, self.alpha, self.beta, sample_weight, self.max_iter, self.eps, self.print_step)
			self.alpha, self.beta = np.array(alpha_C), np.array(beta_C)
		
		if self.loss == 'psi':
			diff_dca = 1. 
			for ite_dca in range(self.max_iter):
				if diff_dca < self.eps:
					break
				beta_old = np.copy(self.beta)
				G = 1.*(Xy.dot(self.beta) < 0)
				self.beta = Xy.T.dot(self.alpha - G)
				# psi_drift = np.dot(Xy, np.sum(Xy * G[:, np.newaxis], axis=0))
				# B = np.dot(G, Xy)
				# drift_new = drift - psi_drift + np.dot(Xy, B)
				if sparse.issparse(Xy):
					diff = 1.
					for ite in range(self.max_iter):
						if diff < self.eps:
							break
						beta_old = np.copy(self.beta)
						for i in range(n):
							if diag[i] != 0:
								delta_tmp = (1. - drift[i] - Xy[i].dot(self.beta)[0]) / diag[i]
								delta_tmp = max(-self.alpha[i], min(sample_weight[i] - self.alpha[i], delta_tmp))
							if diag[i] == 0:
								if Xy[i].dot(self.beta)[0] < 1 - drift[i]:
									delta_tmp = sample_weight[i] - self.alpha[i]
								else:
									delta_tmp = -self.alpha[i]
							self.alpha[i] = self.alpha[i] + delta_tmp
							self.beta = np.array(self.beta + delta_tmp*Xy[i])[0]
						diff = np.sum(np.abs(beta_old - self.beta))/np.sum(np.abs(beta_old+1e-10))
						if self.print_step == 1:
							if ite > 0:
								print("ite %s coordinate descent with diff: %.3f;" %(ite, diff))
				else:
					alpha_C, beta_C = CD_drift(Xy, diag, drift, self.alpha, self.beta, sample_weight, self.max_iter, self.eps, self.print_step)
					self.alpha, self.beta = np.array(alpha_C), np.array(beta_C)
				diff_dca = np.sum(np.abs(self.beta - beta_old)) / (np.sum(np.abs(beta_old))+1e-10)
				print("DCA fits psi-loss with diff: %.3f" %diff_dca)
				# obj_psi = np.sum(np.minimum(np.maximum(1 - self.decision_function(X,drift)*y, 0),1)) + .5*self.beta.dot(self.beta)
				# print(obj_psi)
		# for ite in range(self.max_iter):
		# 	if diff < self.eps:
		# 		break
		# 	beta_old = np.copy(self.beta)
		# 	for i in range(n):
		# 		if diag[i] != 0:
		# 			delta_tmp = (1. - drift[i] - np.dot(self.beta, Xy[i])) / diag[i]
		# 			delta_tmp = max(-self.alpha[i], min(sample_weight[i] - self.alpha[i], delta_tmp))
		# 		if diag[i] == 0:
		# 			if np.dot(self.beta, Xy[i]) < 1 - drift[i]:
		# 				delta_tmp = sample_weight[i] - self.alpha[i]
		# 			else:
		# 				delta_tmp = -self.alpha[i]
		# 		self.alpha[i] = self.alpha[i] + delta_tmp
		# 		self.beta = self.beta + delta_tmp*Xy[i]
		# 	obj = self.dual_obj(Xy=Xy, drift=drift)
		# 	diff = np.sum(np.abs(beta_old - self.beta))/np.sum(np.abs(beta_old+1e-10))
		# 	if self.print_step:
		# 		if ite > 0:
		# 			print("ite %s coordinate descent with diff: %.3f; obj: %.3f" %(ite, diff, obj))

	def dual_obj(self, Xy, drift):
		## compute the dual objective function
		sum_tmp = np.dot(self.alpha, Xy)
		return np.dot(1. - drift, self.alpha) - .5 * np.dot(sum_tmp, sum_tmp)

	def decision_function(self, X, drift):
		return np.dot(X, self.beta) + drift
