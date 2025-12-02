/**
 * Tests for UserInputPrompt component
 * 
 * Tests cover:
 * - Confirmation type rendering and interaction
 * - Selection type with options
 * - Input type with custom text
 * - Option interactions (preset, other, cancel)
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserInputPrompt } from '../UserInputPrompt';

describe('UserInputPrompt Component', () => {
  describe('Confirmation Type', () => {
    it('should render confirmation prompt with message', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="confirmation"
          message="Are you sure you want to proceed?"
          onRespond={onRespond}
        />
      );

      expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
      expect(screen.getByText('✅ 确认')).toBeInTheDocument();
      expect(screen.getByText('❌ 取消')).toBeInTheDocument();
    });

    it('should call onRespond with "确认" when confirm button clicked', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="confirmation"
          message="Confirm action?"
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('✅ 确认'));
      expect(onRespond).toHaveBeenCalledWith('确认');
    });

    it('should call onRespond with "取消" when cancel button clicked', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="confirmation"
          message="Confirm action?"
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('❌ 取消'));
      expect(onRespond).toHaveBeenCalledWith('取消');
    });

    it('should disable buttons when loading', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="confirmation"
          message="Confirm action?"
          onRespond={onRespond}
          isLoading={true}
        />
      );

      const confirmButton = screen.getByText('✅ 确认').closest('button');
      const cancelButton = screen.getByText('❌ 取消').closest('button');

      expect(confirmButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();
    });
  });

  describe('Selection Type', () => {
    const options = ['Option 1', 'Option 2', 'Option 3'];

    it('should render selection prompt with all options', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      expect(screen.getByText('Choose an option:')).toBeInTheDocument();
      expect(screen.getByText('1️⃣ Option 1')).toBeInTheDocument();
      expect(screen.getByText('2️⃣ Option 2')).toBeInTheDocument();
      expect(screen.getByText('3️⃣ Option 3')).toBeInTheDocument();
      expect(screen.getByText('➕ 其他')).toBeInTheDocument();
      expect(screen.getByText('❌ 取消')).toBeInTheDocument();
    });

    it('should call onRespond with selected option', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('2️⃣ Option 2'));
      expect(onRespond).toHaveBeenCalledWith('Option 2');
    });

    it('should show custom input when "其他" is clicked', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('➕ 其他'));

      expect(screen.getByPlaceholderText('请输入自定义选项...')).toBeInTheDocument();
      expect(screen.getByText('提交')).toBeInTheDocument();
      expect(screen.getByText('返回')).toBeInTheDocument();
    });

    it('should submit custom input', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      // Click "其他"
      await user.click(screen.getByText('➕ 其他'));

      // Type custom input
      const input = screen.getByPlaceholderText('请输入自定义选项...');
      await user.type(input, 'Custom option');

      // Submit
      await user.click(screen.getByText('提交'));

      expect(onRespond).toHaveBeenCalledWith('Custom option');
    });

    it('should not submit empty custom input', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      // Click "其他"
      await user.click(screen.getByText('➕ 其他'));

      // Try to submit without typing
      const submitButton = screen.getByText('提交').closest('button');
      expect(submitButton).toBeDisabled();
    });

    it('should return to options from custom input', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      // Click "其他"
      await user.click(screen.getByText('➕ 其他'));

      // Click "返回"
      await user.click(screen.getByText('返回'));

      // Should show options again
      expect(screen.getByText('1️⃣ Option 1')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('请输入自定义选项...')).not.toBeInTheDocument();
    });

    it('should call onRespond with "取消" when cancel clicked', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose an option:"
          options={options}
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('❌ 取消'));
      expect(onRespond).toHaveBeenCalledWith('取消');
    });
  });

  describe('Input Type', () => {
    it('should render input prompt with text field', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Please provide details:"
          onRespond={onRespond}
        />
      );

      expect(screen.getByText('Please provide details:')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('请输入...')).toBeInTheDocument();
      expect(screen.getByText('提交')).toBeInTheDocument();
      expect(screen.getByText('取消')).toBeInTheDocument();
    });

    it('should submit input value', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter your name:"
          onRespond={onRespond}
        />
      );

      const input = screen.getByPlaceholderText('请输入...');
      await user.type(input, 'John Doe');

      await user.click(screen.getByText('提交'));

      expect(onRespond).toHaveBeenCalledWith('John Doe');
    });

    it('should not submit empty input', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter something:"
          onRespond={onRespond}
        />
      );

      const submitButton = screen.getByText('提交').closest('button');
      expect(submitButton).toBeDisabled();
    });

    it('should trim whitespace from input', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter text:"
          onRespond={onRespond}
        />
      );

      const input = screen.getByPlaceholderText('请输入...');
      await user.type(input, '  test value  ');

      await user.click(screen.getByText('提交'));

      expect(onRespond).toHaveBeenCalledWith('test value');
    });

    it('should call onRespond with "取消" when cancel clicked', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter something:"
          onRespond={onRespond}
        />
      );

      fireEvent.click(screen.getByText('取消'));
      expect(onRespond).toHaveBeenCalledWith('取消');
    });

    it('should disable inputs when loading', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter something:"
          onRespond={onRespond}
          isLoading={true}
        />
      );

      const input = screen.getByPlaceholderText('请输入...');
      const submitButton = screen.getByText('提交').closest('button');
      const cancelButton = screen.getByText('取消').closest('button');

      expect(input).toBeDisabled();
      expect(submitButton).toBeDisabled();
      expect(cancelButton).toBeDisabled();
    });

    it('should submit on Enter key', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter text:"
          onRespond={onRespond}
        />
      );

      const input = screen.getByPlaceholderText('请输入...');
      await user.type(input, 'Test value{Enter}');

      expect(onRespond).toHaveBeenCalledWith('Test value');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty options array', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose:"
          options={[]}
          onRespond={onRespond}
        />
      );

      // Should still show "其他" and "取消"
      expect(screen.getByText('➕ 其他')).toBeInTheDocument();
      expect(screen.getByText('❌ 取消')).toBeInTheDocument();
    });

    it('should handle undefined options', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose:"
          onRespond={onRespond}
        />
      );

      // Should still render without errors
      expect(screen.getByText('Choose:')).toBeInTheDocument();
    });

    it('should clear custom input after submission', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      const { rerender } = render(
        <UserInputPrompt
          type="selection"
          message="Choose:"
          options={['Option 1']}
          onRespond={onRespond}
        />
      );

      // Click "其他"
      await user.click(screen.getByText('➕ 其他'));

      // Type and submit
      const input = screen.getByPlaceholderText('请输入自定义选项...');
      await user.type(input, 'Custom');
      await user.click(screen.getByText('提交'));

      // Rerender with same props
      rerender(
        <UserInputPrompt
          type="selection"
          message="Choose:"
          options={['Option 1']}
          onRespond={onRespond}
        />
      );

      // Should be back to options view
      expect(screen.queryByPlaceholderText('请输入自定义选项...')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper button roles', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="confirmation"
          message="Confirm?"
          onRespond={onRespond}
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2);
    });

    it('should focus input on mount for input type', () => {
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="input"
          message="Enter:"
          onRespond={onRespond}
        />
      );

      const input = screen.getByPlaceholderText('请输入...');
      expect(input).toHaveFocus();
    });

    it('should focus custom input when shown', async () => {
      const user = userEvent.setup();
      const onRespond = jest.fn();
      
      render(
        <UserInputPrompt
          type="selection"
          message="Choose:"
          options={['Option 1']}
          onRespond={onRespond}
        />
      );

      await user.click(screen.getByText('➕ 其他'));

      const input = screen.getByPlaceholderText('请输入自定义选项...');
      expect(input).toHaveFocus();
    });
  });
});
